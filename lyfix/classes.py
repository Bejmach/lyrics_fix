from ntpath import isdir
from typing import Self, override
import re
import os


class LyricsController:
    def __init__(
        self,
        line_fix_content: bool = True,
        repetitions_erase: bool = True,
        repetitions_max_time_change: int = 25,
        spaces_between_timestamps: bool = True,
        timestamp_repetitions_erase: bool = True,
        erase_style_repetitions: bool = True,
        lyrics_format: str = "lrc",
        lang_priority: list[str] = ["en", "jp", "pl", "ru"],
    ) -> None:
        self.lyrics_data: dict[str, LyricsData] = {}

        self.line_fix_content: bool = line_fix_content
        self.repetitions_erase: bool = repetitions_erase
        self.repetitions_max_time_change: int = (
            repetitions_max_time_change  # Max time change between lines to consider as repetition
        )
        self.spaces_between_timestamps: bool = spaces_between_timestamps
        self.timestamp_repetitions_erase: bool = (
            timestamp_repetitions_erase  # erases lines that are duplicated between timestamps
        )
        self.erase_style_repetitions: bool = erase_style_repetitions

        if lyrics_format in self.supported_formats():
            self.lyrics_format: str = lyrics_format
        else:
            lyrics_format = self.supported_formats()[0]

        self.lang_priority: list[str] = lang_priority

    @staticmethod
    def supported_formats() -> list[str]:
        return ["lrc"]

    def add_lyrics_from_directory(
        self, directory: str, recursively: bool = False
    ) -> None:
        if not os.path.isdir(directory):
            print(f"Error, path ${directory} is not a valid directory path")
            return
        if recursively:
            f = get_files_recursively(directory)
        else:
            f = get_files_non_recursively(directory)
        for file_dir, file in f:
            data: LyricsData | None = LyricsData.from_file(file_dir, file)
            if data is None:
                continue
            if self.lyrics_data.get(data.name) is not None:
                old_data: LyricsData = self.lyrics_data[data.name]
                new_priority = data.get_lang_priority(self.lang_priority)
                old_priority = old_data.get_lang_priority(self.lang_priority)
                if new_priority < old_priority:
                    self.lyrics_data[data.name] = data
            else:
                self.lyrics_data[data.name] = data

    def fix_style_repetitions(self) -> None:
        for name in self.lyrics_data:
            data = self.lyrics_data[name]
            data.erase_style_repetitions()

    def fix_timestamp_repetitions(self) -> None:
        for name in self.lyrics_data:
            data = self.lyrics_data[name]
            data.erase_timestamp_repetitions()

    def fix_repetitions(self) -> None:
        for name in self.lyrics_data:
            data = self.lyrics_data[name]
            data.erase_repetitions(self.repetitions_max_time_change)

    def add_spaces(self) -> None:
        for name in self.lyrics_data:
            data = self.lyrics_data[name]
            data.add_spaces_between_timestamps()

    def fix_content(self) -> None:
        for name in self.lyrics_data:
            data = self.lyrics_data[name]
            data.fix_line_content()

    def save_lyrics(self, overwrite_output: str | None = None) -> None:
        if overwrite_output != None:
            if not os.path.isdir(overwrite_output):
                print(f"Error, path ${overwrite_output} is not a valid directory path")
                return
        for name in self.lyrics_data:
            data = self.lyrics_data[name]
            data.save_file(overwrite_output)

    # order matters, because if fix_content will be run before style_repetition, it wont have any styles to check for repetitions
    def fix_lyrics(self) -> None:
        if self.erase_style_repetitions:
            self.fix_style_repetitions()
        if self.line_fix_content:
            self.fix_content()
        if self.timestamp_repetitions_erase:
            self.fix_timestamp_repetitions()
        if self.repetitions_erase:
            self.fix_repetitions()
        if self.spaces_between_timestamps:
            self.add_spaces()


def get_files_recursively(directory: str) -> list[list[str]]:
    f: list[list[str]] = []

    for root, _, files in os.walk(directory):
        for file in files:
            f.append([root, file])

    return f


def get_files_non_recursively(directory: str) -> list[list[str]]:
    files = [[directory, f] for f in os.listdir(directory) if os.path.isfile(f)]
    return files


class LyricsLine:
    def __init__(self, time: int, content: str) -> None:
        self.timestamp: int = time
        self.content: str = content

    @override
    def __str__(self) -> str:
        return f"[{self.get_time()}]{self.content}"

    def get_time(self) -> str:
        return stamp_to_time(self.timestamp)

    def fix_content(self) -> None:
        self.content = fix_line_content(self.content)


def fix_line_content(content: str) -> str:
    # strip zero width characters
    content = re.sub(r"[\u200b\u200c\u200d\uFEFF]", "", content)

    erase = ["\\n", "\\t", "\\r", "\\h"]
    replace = [["\\\\", "\\"], ['\\"', '"'], ["\\'", "'"]]
    for symbol in erase:
        content = content.replace(symbol, "")
    for pair in replace:
        content = content.replace(pair[0], pair[1])
    lb_position = content.find("<")
    rb_position = content.find(">")
    pos = 0
    while (lb_position != -1) and (rb_position != -1):
        if lb_position < rb_position:
            content = content[: lb_position + pos] + content[rb_position + 1 + pos :]
            pos -= rb_position - lb_position - 1
        pos += max(rb_position, lb_position) - 1
        lb_position = content[pos:].find("<")
        rb_position = content[pos:].find(">")
    return content


class LyricsData:
    def __init__(
        self,
        name: str = "",
        directory: str = "",
        ext: str = "",
        lang: str = "",
        lines: list[LyricsLine] = [],
    ) -> None:
        self.name: str = name
        self.directory: str = directory
        self.ext: str = ext
        self.lang: str = lang
        self.lines: list[LyricsLine] = lines
        self.metadata: list[str] = []

    @classmethod
    def from_file(cls, directory: str, filename: str) -> Self | None:
        file = open(os.path.join(directory, filename))
        lines = file.readlines()
        file.close()

        dot_count = filename.count(".")

        pos = filename.rfind(".")
        ext = filename[pos + 1 :]

        lang = ""
        name = ""

        if dot_count < 2:
            return None
        else:
            pos = filename.rfind(".", 0, pos)
            lang = filename[pos + 1 : filename.rfind(".")]
            name = filename[:pos]

        if not is_lang_code(lang):
            return None

        lyrics_data = cls(name, directory, ext, lang, [])

        metadata: bool = True

        for line in lines:
            if line == "\n":
                metadata = False
                continue
            if metadata:
                lyrics_data.metadata.append(line)
                continue
            time = line[1 : line.find("]")]
            content = line[line.find("]") + 1 :]
            lyrics_line = LyricsLine(time_to_stamp(time), content)
            lyrics_data.lines.append(lyrics_line)

        return lyrics_data

    @override
    def __str__(self) -> str:
        line_str = ""
        for line in self.lines:
            line_str += str(line)
        return f"Name: {self.name}\nLang: {self.lang}\nExt: {self.ext}\nMetadata: {self.metadata}\nLines:\n{line_str}"

    def fix_line_content(self) -> None:
        for line in self.lines:
            line.fix_content()

    ## Delete reperitions that are changed in span of last max_time_change hundreds of a second
    def erase_repetitions(self, max_time_change: int = 50) -> None:
        new_lines: list[LyricsLine] = []
        last_line: LyricsLine = self.lines[0]
        for i in range(1, len(self.lines)):
            cur_line: LyricsLine = self.lines[i]
            prev_line: LyricsLine = self.lines[i - 1]
            if (
                last_line.content == cur_line.content
                and cur_line.timestamp - prev_line.timestamp < max_time_change
            ):
                continue
            new_lines.append(last_line)
            last_line = cur_line
        new_lines.append(last_line)
        self.lines = new_lines

    def add_spaces_between_timestamps(self) -> None:
        new_lines: list[LyricsLine] = []
        for i in range(1, len(self.lines)):
            cur_line: LyricsLine = self.lines[i]
            prev_line: LyricsLine = self.lines[i - 1]
            if cur_line.content == "\n" or prev_line.content == "\n":
                continue
            new_lines.append(prev_line)
            if cur_line.timestamp != prev_line.timestamp:
                new_lines.append(LyricsLine(cur_line.timestamp - 1, "\n"))
        new_lines.append(self.lines[-1])
        self.lines = new_lines

    # Some sick fucker decided to add repeated lines like that
    # [time1]line1
    #
    # [time2]line1
    # [time2]line2
    # and now I need to fix it...
    # also wtf is going on with all those subtitles in "https://www.youtube.com/watch?v=wFLn_d51bNc"
    # Don't take me wrong. I think it's very cool idea... But still
    # this erases repetitions only if something changed in timestanp, so it leaves all exactly repeated part
    # I HATE STRING MANIPULATION!!!
    def erase_timestamp_repetitions(self) -> None:
        new_lines: list[LyricsLine] = []
        cur_timestamp = self.lines[0].timestamp
        next_timestamp = 0
        for line in self.lines:
            if line.timestamp > cur_timestamp:
                next_timestamp = line.timestamp
                break
            next_timestamp = -1
        cur_lines = [line for line in self.lines if line.timestamp == cur_timestamp]
        new_lines.extend(cur_lines)
        while next_timestamp != -1:
            cur_lines = [line for line in self.lines if line.timestamp == cur_timestamp]
            next_lines = [
                line for line in self.lines if line.timestamp == next_timestamp
            ]
            if len(next_lines) <= len(cur_lines):
                new_lines.extend(next_lines)
            else:
                iterator: int = len(cur_lines)
                change_id: int = len(cur_lines)
                for i in range(iterator):
                    cur_line = cur_lines[i]
                    next_line = next_lines[i]
                    if cur_line.content != next_line.content:
                        change_id = i
                        break
                next_unique = next_lines[change_id:]
                new_lines.extend(next_unique)

            cur_timestamp = next_timestamp
            for line in self.lines:
                if line.timestamp > cur_timestamp:
                    next_timestamp = line.timestamp
                    break
                next_timestamp = -1
        self.lines = new_lines

    # CIRCUSP/VOCACIRCUS, WHY ARE YOUR LYRICS SO FUCKED UP!!!! I DONT WANT TO MAKE THIS ANYMORE!!!!
    # Damn, I didn't checked how Eves lyrics looks like... fuck
    # At this point it would be more efficient to manually edit lyrics, but what's fun in that
    def erase_style_repetitions(self) -> None:
        style_brackets: list[list[str]] = [["<i>", "</i>"], ["<b>", "</b>"]]
        new_lines: list[LyricsLine] = []
        new_lines.append(self.lines[0])
        for i in range(1, len(self.lines)):
            cur_line: LyricsLine = self.lines[i]
            prev_line: LyricsLine = self.lines[i - 1]
            cur_style_counter: int = 0
            prev_style_counter: int = 0
            for bracket in style_brackets:
                cur_style_counter += min(
                    cur_line.content.count(bracket[0]),
                    cur_line.content.count(bracket[1]),
                )
                prev_style_counter += min(
                    prev_line.content.count(bracket[0]),
                    prev_line.content.count(bracket[1]),
                )
            if cur_style_counter != 0 or prev_style_counter != 0:
                cur_line_content = fix_line_content(cur_line.content).replace("\n", "")
                prev_line_content = fix_line_content(prev_line.content).replace(
                    "\n", ""
                )
                if cur_line_content != prev_line_content:
                    new_lines.append(cur_line)
            else:
                new_lines.append(cur_line)

        self.lines = new_lines

    def get_lang_priority(self, lang_priority: list[str]) -> int:
        id = 0
        for lang in lang_priority:
            if self.lang.startswith(lang):
                return id
            id += 1
        return len(lang_priority)

    def get_file_data(self) -> list[str]:
        filename = f"{self.name}.{self.ext}"
        content = ""
        for meta in self.metadata:
            content += meta
        content += "\n"
        for line in self.lines:
            content += str(line)

        return [self.directory, filename, content]

    def save_file(self, overwrite_output: str | None) -> None:
        directory, filename, content = self.get_file_data()
        if overwrite_output != None and len(overwrite_output) != 0:
            filepath = os.path.join(overwrite_output, filename)
        else:
            filepath = os.path.join(directory, filename)
        f = open(filepath, "w")
        _ = f.write(content)
        f.close()


def time_to_stamp(time: str) -> int:
    parts = re.split(r"[:.]", time)
    min = int(parts[-3])
    sec = int(parts[-2])
    ms = int(parts[-1])

    return ms + sec * 100 + min * 60 * 100


def stamp_to_time(stamp: int) -> str:
    min = stamp // 6000
    stamp = stamp % 6000

    sec = stamp // 100
    ms = stamp % 100

    return f"{min:02d}:{sec:02d}.{ms:02d}"


def is_lang_code(code: str) -> bool:
    return bool(re.fullmatch(r"[a-z]{2}(-[A-Z]{2})?", code))
