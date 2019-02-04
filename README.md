# vviz
A "video visualiser" for Python

Essentially a parser for ffprobe and mp4dump (required), which creates interactive graphs with plot.ly

The current version shows:
- Frames (I (including IDR), P, B) with size
- Bitrate
- Groups of Pictures (GOPs)
- MP4 Fragments 

## Example

![screenshot](https://raw.githubusercontent.com/wabiloo/vviz_py/master/docs/screenshot.png)

## Requirements
- ffprobe (part of most [ffmpeg](https://www.ffmpeg.org/download.html) packages)
- [mp4dump](https://www.bento4.com/documentation/mp4dump/)

## Usage

```
usage: usage: vviz.py [-h] 
               [--ffprobe-exec FFPROBE_EXEC]
               [--mp4dump-exec MP4DUMP_EXEC] 
               [--intervals INTERVALS]
               [--streams STREAMS]
               path_to_file
```
where `INTERVALS` and `STREAMS` use the format used by [ffprobe](https://ffmpeg.org/ffprobe.html)

