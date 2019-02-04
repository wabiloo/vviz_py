import unittest
import json
from ffprobe_parser import *
from mp4dump_parser import *
from models import *
from datetime import datetime, timedelta


def sec2ts(sec):
    return datetime.fromtimestamp(sec, tz=pytz.UTC)


class Test(unittest.TestCase):

    def setUp(self):
        self.framerate = 50
        self.timebase = 1 / 10000000

        with open('test_cases.json') as jsonfile:
            self.externaldata = json.load(jsonfile)

    def test_frame(self):
        frame = Frame(frame_rate=self.framerate, time_base=self.timebase, position=5)
        frame.parse_from_json({
            "pkt_pts": 400000,
            "pkt_size": "4440",
            "key_frame": 0,
            "pict_type": "B",
            "media_type": "video",
        })
        self.assertEquals(frame.position, 5)
        self.assertEquals(frame.size, 4440 * 8)
        self.assertEquals(frame.pict_type, 'B')
        self.assertEquals(frame.key_frame, 0)
        self.assertEquals(frame.start_time, sec2ts(0.04))
        self.assertEquals(frame.duration, timedelta(seconds=0.02))
        self.assertEquals(frame.end_time, sec2ts(0.06))
        self.assertEquals(frame.media_type, 'video')
        self.assertEquals(type(frame), BFrame)

        # changing framerate changes the duration of a frame
        frame.frame_rate = 25
        self.assertEquals(frame.duration, timedelta(seconds=0.04))
        self.assertEquals(frame.end_time, sec2ts(0.08))

    def test_iframes(self):
        iframe = Frame()
        iframe.parse_from_json({
            "pkt_pts": 400000,
            "pkt_size": "4440",
            "key_frame": 0,
            "pict_type": "I",
            "media_type": "video",
        })
        self.assertIsNone(iframe.position)
        self.assertEquals(iframe.pict_type, 'I')
        self.assertEquals(iframe.key_frame, 0)
        self.assertEquals(type(iframe), IFrame)
        self.assertEquals(str(iframe), 'i')

        idrframe = Frame()
        idrframe.parse_from_json({
            "pkt_pts": 400000,
            "pkt_size": "4440",
            "key_frame": 1,
            "pict_type": "I",
            "media_type": "video",
        })
        self.assertEquals(idrframe.pict_type, 'I')
        self.assertEquals(idrframe.key_frame, 1)
        self.assertEquals(type(idrframe), IDRFrame)
        self.assertEquals(str(idrframe), 'I')

    def test_closed_gop(self):
        json = [{
                "pkt_pts": 200000,
                "pkt_size": "104000",
                "key_frame": 1,
                "pict_type": "I",
                "media_type": "video",
            },
            {
                "pkt_pts": 400000,
                "pkt_size": "4440",
                "key_frame": 0,
                "pict_type": "B",
                "media_type": "video",
            },
            {
                "pkt_pts": 600000,
                "pkt_size": "1324",
                "key_frame": 0,
                "pict_type": "B",
                "media_type": "video",
            },
            {
                "pkt_pts": 800000,
                "pkt_size": "10612",
                "key_frame": 0,
                "pict_type": "P",
                "media_type": "video",
            }
        ]

        gop = GOP()
        frames = []
        for idx, jframe in enumerate(json):
            frame = Frame(time_base=self.timebase, frame_rate=self.framerate, position=idx)
            frame.parse_from_json(jframe)
            gop.add_frame(frame)

        self.assertEquals(gop.length, 4)
        self.assertEquals(gop.start_time, sec2ts(0.02))
        self.assertEquals(gop.end_time, sec2ts(0.10))
        self.assertEquals(gop.size, (104000+4440+1324+10612)*8)
        self.assertTrue(gop.closed)

    def test_open_gop(self):
        json = [{
            "pkt_pts": 200000,
            "pkt_size": "104000",
            "key_frame": 0,
            "pict_type": "I",
            "media_type": "video",
        },
        {
            "pkt_pts": 400000,
            "pkt_size": "4440",
            "key_frame": 0,
            "pict_type": "B",
            "media_type": "video",
        }]

        gop = GOP()
        frames = []
        for idx, jframe in enumerate(json):
            frame = Frame(time_base=self.timebase, frame_rate=self.framerate)
            frame.parse_from_json(jframe)
            gop.add_frame(frame)

        self.assertEquals(gop.length, 2)
        self.assertFalse(gop.closed)


    def test_ffprobe_parser(self):
        json = self.externaldata['test1']
        ffresp = FFProbeResponse(json)
        streams = ffresp.get_streams()
        self.assertEquals(len(streams), 1)
        self.assertTrue(isinstance(streams[0], Stream))
        self.assertEquals(streams[0].index, 0)

        frames = ffresp.get_frames_for_stream(streams[0])
        self.assertEquals(len(frames), 21)
        self.assertTrue(isinstance(frames[0], Frame))
        self.assertTrue(isinstance(frames[-1], Frame))
        self.assertTrue(frames[0].duration, 0.02)
        self.assertEquals(frames[0].position, 1)


    def test_stream_from_ffprobe(self):
        json = self.externaldata['test1']
        ffresp = FFProbeResponse(json)
        stream0 = Stream(origin=ffresp, stream_index=0)
        self.assertEquals(len(stream0.frames), 21)
        self.assertEquals(len(stream0.get_frames_for_type(IFrame)), 4)
        self.assertEquals(len(stream0.get_frames_for_type(IFrame, strict=True)), 2)

        self.assertTrue(isinstance(stream0.frames[0], Frame))
        self.assertTrue(isinstance(stream0.frames[-1], Frame))
        self.assertEquals(stream0.frames[0].duration, timedelta(seconds=0.02))
        self.assertEquals(stream0.frames[0].position, 1)

        self.assertEquals(len(stream0.gops), 4)
        self.assertEquals(len(stream0.gops[0].frames), 5)
        self.assertEquals(len(stream0.gops[2].frames), 6)
        self.assertEquals(str(stream0.gops[0]), "GOP: IBBBP 5 CLOSED")
        self.assertEquals(str(stream0.gops[1]), "GOP: iBBPB 5 OPEN")

    def test_fragment(self):
        moof = {
          "name":"moof",
          "header_size":8,
          "size":484,
          "children":[
          {
            "name":"mfhd",
            "header_size":12,
            "size":16,
            "sequence number":9
          },
          {
            "name":"traf",
            "header_size":8,
            "size":460,
            "children":[
            {
              "name":"tfhd",
              "header_size":12,
              "size":24,
              "track ID":2,
              "default sample duration":400000,
              "default sample flags":16842752
            },
            {
              "name":"tfdt",
              "header_size":12,
              "size":20,
              "base media decode time":153600000
            },
            {
              "name":"trun",
              "header_size":12,
              "size":408,
              "sample count":48,
              "data offset":492,
              "first sample flags":33554432
            }]
          }]
        }

        mdat = {
          "name":"mdat",
          "header_size":8,
          "size":66055
        }

        track = MP4Track(track_id=2)
        track.time_scale = 10000000

        fragment = Fragment(moof, mdat, track, 5)
        self.assertEquals(fragment.position, 5)
        self.assertEquals(fragment.start_time, sec2ts(15.36))
        self.assertEquals(fragment.length, 48)
        self.assertEquals(fragment.duration, timedelta(seconds=0.04*48))
        self.assertEquals(fragment.end_time, sec2ts(15.36+0.04*48))
        self.assertEquals(fragment.size, 66055*8)

    def test_track_from_mp4dump(self):
        json = self.externaldata['mp4dump_test1']
        resp = MP4DumpResponse(json)
        track0 = MP4Track(parser=resp, track_id=2)

        self.assertEquals(track0.time_scale, 10000000)
        self.assertEquals(len(track0.fragments), 8)

        frag0 = track0.fragments[0]
        self.assertEquals(frag0.start_time, sec2ts(0))
        self.assertEquals(frag0.duration, timedelta(seconds=0.04*48))
        self.assertEquals(frag0.position, 1)

        last = track0.fragments[-1]
        self.assertEquals(last.start_time, sec2ts(13.44))


if __name__ == 'main':
    unittest.main()