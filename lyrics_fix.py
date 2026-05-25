from typing import override
import os
import re


class LyricsLine:
    def __init__(self, time: int, content: str) -> None:
        self.timestamp: int = time
        self.content: str = content

    @override
    def __str__(self) -> str:
        return f"[{self.get_time()}]{self.content}"

    def get_time(self) -> str:
        return stamp_to_time(self.timestamp)


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

    def add_space_between_lines(self) -> None:
        new_lines: list[LyricsLine] = []
        for i in range(1, len(self.lines)):
            cur_line: LyricsLine = self.lines[i]
            prev_line: LyricsLine = self.lines[i - 1]
            new_lines.append(prev_line)
            if cur_line.content == "\n" or prev_line.content == "\n":
                continue
            if cur_line.timestamp != prev_line.timestamp:
                new_lines.append(LyricsLine(cur_line.timestamp - 1, "\n"))
        new_lines.append(self.lines[-1])
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
        f.close


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


def get_lang_priority(lyrics_data: LyricsData, lang_priority: list[str]) -> int:
    id = 0
    for lang in lang_priority:
        if lyrics_data.lang.startswith(lang):
            return id
        id += 1
    return len(lang_priority)


def read_lyrics(filename: str) -> LyricsData:
    file = open(filename)
    lines = file.readlines()
    file.close()

    pos = filename.rfind(".")
    ext = filename[pos + 1 :]

    pos = filename.rfind(".", 0, pos)
    lang = filename[pos + 1 : filename.rfind(".")]
    name = filename[:pos]

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
        lyrics_line = LyricsLine(time_to_stamp(time), content)
        lyrics_data.lines.append(lyrics_line)

    return lyrics_data


if __name__ == "__main__":
    lang_priority = ["en", "jp", "pl", "ru"]

    cwd = os.getcwd()
    f = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        for file in filenames:
            if file.endswith(".lrc"):
                f.append(file)
        break
    lyrics: dict[str, LyricsData] = {}
    for file in f:
        lyric_data = read_lyrics(file)
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
        lyric.add_space_between_lines()
        lyric.save_file(cwd)
