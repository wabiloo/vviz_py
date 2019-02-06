import subprocess
import json
import models


class MP4DumpCommand(object):
    def __init__(self, executable='mp4dump', filename=None):
        self._command = '"{mp4dump}" --format json {filename}'.format(mp4dump=executable, filename=filename)

        print("Executing mp4dump to extract track and fragment information")
        print(self._command)
        print()

    def call(self):
        response = subprocess.check_output(self._command, shell=True, stderr=None)
        jresponse = json.loads(response)
        return MP4DumpResponse(jresponse)


class MP4DumpResponse(object):
    def __init__(self, j):
        self._json = j

    # TODO: cater for multiple tracks
    def get_info_for_track(self, track):
        if isinstance(track, models.MP4Track):
            for idx, box in enumerate(self._json):
                if box['name'] == 'moov':
                    # TODO - crude!  put more logic for multiple use cases (variable structure)
                    track.duration = box['children'][0]['duration'] / box['children'][0]['timescale']

                # scale factor for decode timings
                if box['name'] == 'sidx':
                    track.time_scale = box['timescale']
        else:
            raise Exception("'track' argument should be a MP4Track")

    # TODO: cater for multiple tracks
    def get_fragments_for_track(self, track):
        fragments = []
        moof = None
        mdat = None
        count = 1

        if isinstance(track, models.MP4Track):
            for box in self._json:
                # start of a fragment
                if box['name'] == 'moof':
                    moof = box

                # data from segment
                if box['name'] == 'mdat':
                    mdat = box

                    # mdat is the last element required to create a fragment
                    # no moof would mean non-fragmented MP4
                    if moof and mdat:
                        fragment = models.Fragment(moof=moof, mdat=mdat, track=track, position=count)
                        fragments.append(fragment)
                        count+=1

            return fragments
        else:
            raise Exception("'track' argument should be a MP4Track")




