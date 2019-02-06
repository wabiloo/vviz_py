import subprocess
import json
import models


class FFProbeCommand(object):
    def __init__(self, executable='ffprobe', filename=None, streams='v:0', intervals=None):
        interval_param = "-read_intervals {}".format(intervals) if intervals else ""

        # TODO - pass parameters to restrict the ffprobe dimensions returned
        self._command = \
            '"{ffexec}" -hide_banner -loglevel warning -select_streams {streams} {intervals} -show_frames -show_streams -print_format json {filename}' \
            .format(ffexec=executable,
                    filename=filename,
                    intervals=interval_param,
                    streams=streams)

        print("Executing ffprobe to extract stream and frame information")
        print(self._command)
        print()

    def call(self):
        response = subprocess.check_output(self._command, shell=True, stderr=None)
        jresponse = json.loads(response)
        return FFProbeResponse(jresponse)

    # @property
    # def filename(self):
    #     return self._filename
    #
    # @filename.setter
    # def filename(self, new_filename):
    #     self._filename = new_filename


class FFProbeResponse(object):
    def __init__(self, j):
        self._json = j

    @property
    def streams(self):
        return self._json['streams']

    @property
    def frames(self):
        return self._json['frames']

    # TODO: cater for multiple streams
    def get_streams(self):
        streams = []
        if self._json['streams']:
            for idx, jstream in enumerate(self._json['streams']):
                stream = models.Stream()
                stream.parse_from_json(jstream)
                streams.append(stream)
            return streams
        else:
            raise Exception("No streams found in ffprobe response")

    # TODO: cater for multiple streams
    def get_frames_for_stream(self, stream):
        frames = []
        if isinstance(stream, models.Stream):
            if self._json['frames']:
                for idx, jframe in enumerate(self._json['frames']):
                    if jframe['media_type'] == "video" and jframe['stream_index'] == stream.index:
                        frame = models.Frame(time_base=stream.time_base, frame_rate=stream.frame_rate, position=idx+1)
                        frame.parse_from_json(jframe)

                        frames.append(frame)
                return frames
            else:
                raise Exception("No frames found in ffprobe response")
        else:
            raise Exception("'stream' argument should be a Stream")


