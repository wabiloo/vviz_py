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

[Interactive version](http://htmlpreview.github.io/?https://github.com/wabiloo/vviz_py/master/docs/example1.html)

## Requirements
- ffprobe (part of most [ffmpeg](https://www.ffmpeg.org/download.html) packages)
- [mp4dump](https://www.bento4.com/documentation/mp4dump/)
- [orca](https://github.com/plotly/orca) for image output

## Usage

```
usage: vviz.py [-h] [--ffprobe-exec FFPROBE_EXEC]
               [--mp4dump-exec MP4DUMP_EXEC] [--intervals INTERVALS]
               [--streams STREAMS] [-t TITLE] [-b WINDOW]
               [-f [{interactive,svg,pdf,png,webp} [{interactive,svg,pdf,png,webp} ...]]]
               [-r RESOLUTION RESOLUTION]
               path_to_file

Chart generator (interactive and static) for video file analysis (frames,
streams, fragments, gops, etc.)

positional arguments:
  path_to_file          video file to parse

optional arguments:
  -h, --help            show this help message and exit
  --ffprobe-exec FFPROBE_EXEC
                        ffprobe executable. (default: ffprobe)
  --mp4dump-exec MP4DUMP_EXEC
                        mp4dump executable. (default: mp4dump)
  --intervals INTERVALS
                        interval to read from video file (see ffprobe
                        -read_intervals parameter)
  --streams STREAMS     streams to read from video file (see ffprobe
                        -select_streams parameter)
  -t TITLE, --title TITLE
                        title for the chart (in addition to filename)
  -b WINDOW, --window WINDOW
                        size of the window (in seconds) used to calculate
                        average bitrates
  -f [{interactive,svg,pdf,png,webp} [{interactive,svg,pdf,png,webp} ...]], --formats [{interactive,svg,pdf,png,webp} [{interactive,svg,pdf,png,webp} ...]]
                        1 or multiple output formats
  -r RESOLUTION RESOLUTION, --resolution RESOLUTION RESOLUTION
                        resolution (width and height) for output images
```
where `INTERVALS` and `STREAMS` use the format used by [ffprobe](https://ffmpeg.org/ffprobe.html)

