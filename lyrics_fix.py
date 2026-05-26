from random import randint, randrange
from typing import override
import os
import re


class LyricsLine:
    def __init__(self, time: int, content: str, parse_content: bool = False) -> None:
        self.timestamp: int = time
        self.content: str = content
        if parse_content:
            self.fix_content()

    @override
    def __str__(self) -> str:
        return f"[{self.get_time()}]{self.content}"

    def get_time(self) -> str:
        return stamp_to_time(self.timestamp)

    def fix_content(self) -> None:
        erase = ["\\n", "\\t", "\\r", "\\h"]
        replace = [["\\\\", "\\"], ['\\"', '"'], ["\\'", "'"]]
        for symbol in erase:
            self.content = self.content.replace(symbol, "")
        for pair in replace:
            self.content = self.content.replace(pair[0], pair[1])
        lb_position = self.content.find("<")
        rb_position = self.content.find(">")
        pos = 0
        while (lb_position != -1) and (rb_position != -1):
            if lb_position < rb_position:
                self.content = (
                    self.content[: lb_position + pos]
                    + self.content[rb_position + 1 + pos :]
                )
                pos -= rb_position - lb_position - 1
            pos += max(rb_position, lb_position)
            lb_position = self.content[pos:].find("<")
            rb_position = self.content[pos:].find(">")


class LyricsData:
    def __init__(
        self,
        name: str = "",
        ext: str = "",
        lang: str = "",
        lines: list[LyricsLine] = [],
    ) -> None:
        self.name: str = name
        self.ext: str = ext
        self.lang: str = lang
        self.lines: list[LyricsLine] = lines
        self.metadata: list[str] = []

    @override
    def __str__(self) -> str:
        line_str = ""
        for line in self.lines:
            line_str += str(line)
        return f"Name: {self.name}\nLang: {self.lang}\nExt: {self.ext}\nMetadata: {self.metadata}\nLines:\n{line_str}"

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

    def get_file_data(self) -> list[str]:
        filename = f"{self.name}.{self.ext}"
        content = ""
        for meta in self.metadata:
            content += meta
        content += "\n"
        for line in self.lines:
            content += str(line)

        return [filename, content]

    def save_file(self, path: str) -> None:
        filename, content = self.get_file_data()
        filepath = f"{path}/{filename}"
        f = open(filepath, "w")
        _ = f.write(content)
        f.close()


def time_to_stamp(time: str) -> int:
    parts = re.split(r"[:.]", time)
    min = int(parts[-3])
    sec = int(parts[-2])
    ms = int(parts[-1])

    return ms + sec * 100 + min * 60 * 100


def is_lang_code(code: str) -> bool:
    return bool(re.fullmatch(r"[a-z]{2}(-[A-Z]{2})?", code))


def stamp_to_time(stamp: int) -> str:
    min = stamp // 6000
    stamp = stamp % 6000

    sec = stamp // 100
    ms = stamp % 100

    return f"{min:02d}:{sec:02d}.{ms:02d}"


def get_lang_priority(lyrics_data: LyricsData, lang_priority: list[str]) -> int:
    id = 0
    for lang in lang_priority:
        if lyrics_data.lang.startswith(lang):
            return id
        id += 1
    return len(lang_priority)


def read_lyrics(filename: str, parse_lines: bool = False) -> LyricsData | None:
    file = open(filename)
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

    lyrics_data = LyricsData(name, ext, lang, [])

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
        lyrics_line = LyricsLine(time_to_stamp(time), content, parse_lines)
        lyrics_data.lines.append(lyrics_line)

    return lyrics_data


if __name__ == "__main__":
    lang_priority = ["en", "jp", "pl", "ru"]
    parse_lines = True

    cwd = os.getcwd()
    f = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        for file in filenames:
            if file.endswith(".lrc"):
                f.append(file)
        break
    lyrics: dict[str, LyricsData] = {}
    for file in f:
        lyric_data: LyricsData | None = read_lyrics(file, parse_lines)
        if lyric_data is None:
            continue
        if lyrics.get(lyric_data.name) is not None:
            old_lyrics: LyricsData = lyrics[lyric_data.name]
            new_priority = get_lang_priority(lyric_data, lang_priority)
            old_priority = get_lang_priority(old_lyrics, lang_priority)
            if new_priority < old_priority:
                lyrics[lyric_data.name] = lyric_data
        else:
            lyrics[lyric_data.name] = lyric_data

    for name in lyrics:
        lyric: LyricsData = lyrics[name]
        lyric.erase_timestamp_repetitions()
        lyric.erase_repetitions()
        lyric.add_spaces_between_timestamps()
        lyric.save_file(cwd)
