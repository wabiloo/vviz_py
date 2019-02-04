import json
import argparse
import subprocess
import datetime
import statistics

import plotly
import plotly.graph_objs as go

timescale = None
duration = None

def read_mp4dump_boxes_content_from_url(exec, url):
    command = '"{mp4dump}" --format json "{url}"'.format(mp4dump=exec, url=url)

    response_json = subprocess.check_output(command, shell=True, stderr=None)
    return json.loads(response_json)


def extract_fragments(boxes):
    global timescale
    global duration
    fragments = []
    previous_fragment = None
    fragment = {}
    for box in boxes:
        if box['name'] == 'moov':
            duration = box['children'][0]['duration'] / box['children'][0]['timescale']

        # scale factor for decode timings
        if box['name'] == 'sidx':
            timescale = box['timescale']

        # start of a fragment
        if box['name'] == 'moof':
            fragment = {
                'moof': box,
                'decodeTime': box['children'][1]['children'][1]['base media decode time']
            }
            # calculate duration
            if previous_fragment:
                previous_fragment['duration'] = fragment['decodeTime'] - previous_fragment['decodeTime']

        # data from segment
        if box['name'] == 'mdat':
            fragment['mdat'] = box
            fragments.append(fragment)
            previous_fragment = fragment

    # set duration for last fragment
    fragments[-1]['duration'] = duration * timescale - fragments[-1]['decodeTime']

    return fragments


def secs2time(sec):
    min, sec = divmod(sec, 60)
    hr, min = divmod(min, 60)
    return "%d:%02d:%06.3f" % (hr, min, sec)


def render_chart(fragments, chart_title, chart_filename):
    def time_from_fragment(f):
        return f['decodeTime'] / timescale

    def size_from_fragment(f):
        return f['mdat']['size']

    def text_for_fragments(fragments):
        arr = []
        for i, f in enumerate(fragments):
            str = "fragment {}<br>duration: {}<br>size: {}".format(
                i,
                f['duration'] / timescale if 'duration' in f else "",
                f['mdat']['size'],
            )
            arr.append(str)
        return arr

    def get_frame_bar_color(f):
        return 'blue'

    avg_size = statistics.mean([size_from_fragment(f) for f in fragments])

    fragments_bar = go.Bar(
        x=[time_from_fragment(f) for f in fragments],
        y=[size_from_fragment(f) for f in fragments],
        text=text_for_fragments(fragments),
        #width=0.1,
        name='Fragments',
        marker=dict(
            color=[get_frame_bar_color(f) for f in fragments]
        ),
        hoverinfo='x+text'
    )

    avg_size_line = go.Scatter(
        x=[time_from_fragment(fragments[0]), time_from_fragment(fragments[-1])],
        y=[avg_size, avg_size],
        name='Avg Fragment Size',
        marker=dict(
            color='green'
        )
    )

    data = []
    data += [fragments_bar, avg_size_line]

    #print(data)

    layout = go.Layout(
        title=chart_title,
        xaxis=dict(
            title='Time (sec)',
            dtick=60,
            tickfont=dict(
                size=12,
                color='rgb(107, 107, 107)'
            ),
            constrain='range'
        ),
        yaxis=dict(
            title='Frame Size (kbit)',
            titlefont=dict(
                size=16,
                color='rgb(107, 107, 107)'
            ),
            tickfont=dict(
                size=14,
                color='rgb(107, 107, 107)'
            )
        ),
    )

    plotly.offline.plot({
        "data": data,
        "layout": layout
    }, auto_open=True, filename=chart_filename)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Dump Fragment structure of video file')
    parser.add_argument('filename', help='video file to parse')
    parser.add_argument('-t', '--title', dest='title',
                        help='Chart Title (default: from the file name)')
    parser.add_argument('-e', '--mp4dump-exec', dest='mp4dump_exec',
                        help='mp4dump executable. (default: %(default)s)',
                        default='mp4dump')

    args = parser.parse_args()
    filename = args.filename
    title = args.title or "Fragment Size Analysis<br>" + filename
    mp4dump = args.mp4dump_exec

    boxes = read_mp4dump_boxes_content_from_url(mp4dump, filename)

    fragments = extract_fragments(boxes)

    render_chart(fragments, title, filename)

    for i, frag in enumerate(fragments, start=1):
        print("fragment {}: {} - {} - {}".format(
            i,
            frag['mdat']['size'],
            secs2time(frag['decodeTime'] / timescale),
            frag['duration'] / timescale if 'duration' in frag else ""))
