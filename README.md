# Lyrics fix

Small python script to add blank lines between lines with different timestamps.
Supported format lrc. File name format requited <name>.<lang>.lrc(default yt-dlp
format). Creates new files without lang part but uses language to define what
lyrics use if multiple lyrics with same name are present.

Made it becase rmpc does not show multiple lines when they have same timestamp,
and it looked like it was skipping lines
