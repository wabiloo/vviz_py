from functools import reduce
from datetime import datetime, timedelta
import ffprobe_parser, mp4dump_parser
import pytz
import statistics


def sizeof_fmt(num, suffix='b'):
    for unit in ['','K','M','G']:
        if abs(num) < 1000.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1000.0
    return "%.1f%s%s" % (num, 'G', suffix)


def time_to_str(ts, total_duration):
    str = ""
    duration = None
    if isinstance(total_duration, datetime):
        duration = timedelta(microseconds=ts.timestamp())
    elif isinstance(total_duration, timedelta):
        duration = total_duration
    elif isinstance(total_duration, float):
        duration = timedelta(seconds=ts)

    if total_duration > timedelta(hours=1):
        str = ts.strftime("%H:%M:%S.%f")
    else:
        str = ts.strftime("%M:%S.%f")
    # trim microseconds
    return str[:-3]


class Stream(object):
    def __init__(self, origin=None, stream_index=0):
        self._frame_rate = None
        self._time_base = None
        self._duration = None
        self._frames = []
        self.index = stream_index

        if (origin):
            if (isinstance(origin, ffprobe_parser.FFProbeResponse)):
                self._origin = origin
                self.parse_from_json(origin.streams[self.index])
                self._frames = origin.get_frames_for_stream(self)
            else:
                raise Exception("Argument 'origin' should be of type FFProbeResponse")

    @property
    def frame_rate(self):
        return self._frame_rate

    @frame_rate.setter
    def frame_rate(self, frame_rate):
        self._frame_rate = frame_rate

    @property
    def time_base(self):
        return self._time_base

    @time_base.setter
    def time_base(self, time_base):
        self._time_base = time_base

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, duration):
        self._duration = duration

    @property
    def width(self):
        return self._json['width']

    @property
    def height(self):
        return self._json['height']

    # returns all frames
    @property
    def frames(self):
        return self._frames

    # returns all frames of a particular type
    def get_frames_for_type(self, frame_type=None, strict=False):
        if frame_type:
            fs = []
            for f in self.frames:
                if strict:
                    if type(f) == frame_type:
                        fs.append(f)
                else:
                    if isinstance(f, frame_type):
                        fs.append(f)
            return fs
        else:
            return self.frames

    def add_frame(self, frame):
        self._frames.append(frame)

    # Scan frames and extract gops
    @property
    def gops(self):
        gops = []
        gop = GOP(position=1)
        gops.append(gop)
        for idx, frame in enumerate(self.frames):
            if isinstance(frame, IFrame):
                if len(gop.frames):
                    # GOP open and new iframe. Time to close GOP
                    gop = GOP(position=len(gops)+1)
                    gops.append(gop)

            gop.add_frame(frame)

        return gops

    def parse_from_json(self, json):
        self._json = json
        self.frame_rate = eval(json['avg_frame_rate'])
        self.time_base = eval(json['time_base'])
        self.duration = timedelta(seconds=json['duration_ts'] * self.time_base)
        self.index = json['index']

    def to_label(self):
        avg_bitrate = statistics.mean([f.bitrate for f in self.frames])

        span = "<i>Analysis for span <br>{} to {}</i>".format(
            time_to_str(self.frames[0].start_time, self.duration),
            time_to_str(self.frames[-1].end_time, self.duration)
        )

        analysis = "avg bitrate: <b>{avg}</b><br>".format(
            avg=sizeof_fmt(avg_bitrate, 'bps'),
        )

        label = "Stream<br>{w}x{h}<br>duration: <b>{duration}</b><br><br>{span}<br>{analysis}".format(
            duration=str(self.duration)[:-3],
            analysis=analysis,
            span=span,
            w=self.width,
            h=self.height
        )
        return label


class Frame(object):
    def __init__(self, time_base=None, frame_rate=None, position=None):
        self.key_frame = None
        self.pkt_pts = None
        self.pkt_size = None
        self.pict_type = None
        self.media_type = None
        self.time_base = time_base
        self.frame_rate = frame_rate
        self.position = position

    def __str__(self, *args, **kwargs):
        return "frame"

    def parse_from_json(self, json):
        self._json = json
        self.pkt_pts = json['pkt_pts']
        self.pkt_size = int(json['pkt_size'])
        self.pict_type = json['pict_type']
        self.key_frame = json['key_frame']
        self.media_type = json['media_type']
        if self.pict_type == 'B':
            self.__class__ = BFrame
        if self.pict_type == 'P':
            self.__class__ = PFrame
        if self.pict_type == 'I':
            if self.key_frame:
                self.__class__ = IDRFrame
            else:
                self.__class__ = IFrame

    # size in bits
    @property
    def size(self):
        return self.pkt_size * 8

    # duration in sec
    # TODO - it would be better to use pkt_duration_time, particularly for variable framerate
    # However, ffprobe doesn't output it every time...
    @property
    def duration(self):
        if self.frame_rate:
            return timedelta(seconds=1 / self.frame_rate)
        else:
            raise Exception("No framerate defined on the frame")

    # bitrate in bits/s
    @property
    def bitrate(self):
        # To get instantaneous frame bitrate we must consider the frame rate
        if self.frame_rate:
            return self.size * self.frame_rate
        else:
            raise Exception("No framerate defined on the frame")

    @property
    def start_time(self):
        if self.time_base:
            return datetime.fromtimestamp(self.pkt_pts * self.time_base, tz=pytz.UTC)
        else:
            raise Exception("No timebase defined on the frame")

    @property
    def end_time(self):
        if self.time_base:
            return datetime.fromtimestamp((self.pkt_pts * self.time_base) + self.duration.total_seconds(), tz=pytz.UTC)
        else:
            raise Exception("No timebase defined on the frame")

    def to_dict(self):
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'type': self.__class__.__name__,
            'code': self.__repr__(),
            'bitrate': self.bitrate,
            'size': self.size,
            'position': self.position
        }


class BFrame(Frame):
    def __init__(self):
        super().__init__()

    def __repr__(self, *args, **kwargs):
        return "B"

    def __str__(self, *args, **kwargs):
        return repr(self)


class PFrame(Frame):
    def __init__(self):
        super().__init__()

    def __repr__(self, *args, **kwargs):
        return "P"

    def __str__(self, *args, **kwargs):
        return repr(self)


class IFrame(Frame):
    def __init__(self):
        super().__init__()

    def __repr__(self, *args, **kwargs):
        return "i"

    def __str__(self, *args, **kwargs):
        return repr(self)


class IDRFrame(IFrame):
    def __init__(self):
        super().__init__()

    def __repr__(self, *args, **kwargs):
        return "I"

    def __str__(self, *args, **kwargs):
        return repr(self)


class GOP(object):
    def __init__(self, position=None):
        self.closed = False
        self.position = position
        self._frames = []

    @property
    def frames(self):
        return self._frames

    @property
    def length(self):
        return len(self.frames)

    @property
    def size(self):
        return reduce(lambda x, y: x + y.size, self.frames, 0)

    @property
    def start_time(self):
        return self.frames[0].start_time

    @property
    def end_time(self):
        return self.frames[-1].end_time

    @property
    def duration(self):
        return self.end_time - self.start_time

    def add_frame(self, frame):
        self._frames.append(frame)

        if isinstance(frame, IDRFrame):
            self.closed = True

    def __repr__(self, *args, **kwargs):
        frames_repr = ''

        for frame in self.frames:
            frames_repr += str(frame)

        gtype = 'CLOSED' if self.closed else 'OPEN'

        return 'GOP: {frames} {count} {gtype}'.format(frames=frames_repr,
                                                      count=len(self.frames),
                                                      gtype=gtype)

    def to_label(self):
        str = "GOP {pos}<br>{open_or_closed}<br>{nb_pic} frames<br>from {start}<br>{size}".format(
            pos=self.position,
            open_or_closed="CLOSED" if self.closed else "OPEN",
            nb_pic=self.length,
            size=sizeof_fmt(self.size, suffix='b'),
            start=time_to_str(self.start_time, self.duration)
        )
        return str


class MP4Track(object):
    def __init__(self, track_id=None, parser=None):
        self._time_scale = None
        self._duration = None
        self._parser = None
        self._fragments = []
        self.id = track_id

        if parser:
            self._parser = parser
            self.create_from_parser(self._parser)

    @property
    def time_scale(self):
        return self._time_scale

    @time_scale.setter
    def time_scale(self, time_scale):
        self._time_scale = time_scale

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, duration):
        self._duration = duration

    @property
    def fragments(self):
        return self._fragments

    def create_from_parser(self, parser):
        if isinstance(parser, mp4dump_parser.MP4DumpResponse):
            self._parser = parser
            parser.get_info_for_track(self)
            self._fragments = parser.get_fragments_for_track(self)
        else:
            raise Exception("Argument 'origin' should be of type MP4DumpResponse")

    def to_label(self):
        max_size = max([f.size for f in self.fragments])
        avg_size = statistics.mean([f.size for f in self.fragments])

        label = "avg fragment size: <b>{avg}</b><br>max segment size: <b>{max}</b>".format(
            avg=sizeof_fmt(avg_size, "b"),
            max=sizeof_fmt(max_size, "b"),
        )

        return label


class Fragment(object):
    def __init__(self, moof=None, mdat=None, track=None, position=None):
        self._moof = None
        self._mdat = None
        self._track = None

        self.track = track
        self.moof = moof
        self.mdat = mdat
        self.position = position

    @property
    def moof(self):
        return self._moof

    @moof.setter
    def moof(self, moof):
        self._moof = moof

    @property
    def mdat(self):
        return self._mdat

    @mdat.setter
    def mdat(self, mdat):
        self._mdat = mdat

    @property
    def track(self):
        return self._track

    @track.setter
    def track(self, track):
        self._track = track

    @property
    def start_time(self):
        decodeTime = self.moof['children'][1]['children'][1]['base media decode time']
        return datetime.fromtimestamp(decodeTime / self.track.time_scale, tz=pytz.UTC)

    @property
    def length(self):
        sampleCount = self.moof['children'][1]['children'][2]['sample count']
        return sampleCount

    @property
    def duration(self):
        sampleDuration = self.moof['children'][1]['children'][0]['default sample duration']
        return timedelta(seconds=sampleDuration * self.length / self.track.time_scale)

    @property
    def end_time(self):
        return self.start_time + self.duration

    @property
    def size(self):
        return self.mdat['size'] * 8

    def to_label(self):
        str = "Fragment {pos}<br>{nb_pic} samples<br>from {start}<br>length <b>{duration}</b><br>{size}".format(
            pos=self.position,
            nb_pic=self.length,
            size=sizeof_fmt(self.size, suffix='b'),
            start=time_to_str(self.start_time, self.duration),
            duration="{}s".format(self.duration.total_seconds())
        )
        return str
