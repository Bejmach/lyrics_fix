import argparse
import os
from lyfix.classes import LyricsController


def main() -> None:
    cwd: str = os.getcwd()

    parser = argparse.ArgumentParser(
        prog="Lyfix",
        description="A Cli Lyrics parsing tool",
        usage="%(prog)s [options]",
        epilog="Example: lyfix -s",
    )
    parser.add_argument("-R", "--recursive", action="store_true", help="run in subdirs")
    parser.add_argument(
        "-i",
        "--input-directory",
        type=str,
        default=cwd,
        help="tell where to start looking for lyrics files, default to working directory",
    )
    parser.add_argument(
        "-o",
        "--output-directory",
        type=str,
        default=None,
        help="Tell where to save all lyrics files",
    )
    parser.add_argument(
        "-l", "--fix-lines", action="store_true", help="Remove styling chars from lines"
    )
    parser.add_argument(
        "-s",
        "--spaces",
        action="store_true",
        help="add empty lines between different timestamps",
    )
    parser.add_argument(
        "-r",
        "--repetitions",
        type=int,
        default=-1,
        help="Remove repetitions if time between lines less than provided",
    )
    parser.add_argument(
        "-tr",
        "--timestamp-repetitions",
        action="store_true",
        help="Remove first lines from next timestamp if lines are same as first lines from previous timestamp",
    )
    parser.add_argument(
        "-sr",
        "--style-repetitions",
        action="store_true",
        help="Remove repetitions that are different with only style annotations",
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        default="lrc",
        help="lyrics format (currently supporting only .lrc)",
    )
    parser.add_argument(
        "-fl",
        "--format-list",
        action="store_true",
        help="Show supported lyrics formats",
    )
    parser.add_argument(
        "-L",
        "--lang-priority",
        type=str,
        default="en",
        help='priority of lyrics if multiple lyrics with same name found splitted by coma, ex. "en,jp,ru"',
    )

    args = parser.parse_args()
    if args.format_list:
        print(LyricsController.supported_formats())
        return

    lang_priority: list[str] = args.lang_priority.split(",")
    if args.repetitions >= 0:
        repetitions_erase = True
    else:
        repetitions_erase = False
    lyrics: LyricsController = LyricsController(
        args.fix_lines,
        repetitions_erase,
        args.repetitions,
        args.spaces,
        args.timestamp_repetitions,
        args.style_repetitions,
        args.format,
        lang_priority,
    )
    lyrics.add_lyrics_from_directory(args.input_directory, args.recursive)
    lyrics.fix_lyrics()
    lyrics.save_lyrics(args.output_directory)


if __name__ == "__main__":
    main()
