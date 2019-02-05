#!/usr/bin/env python
from __future__ import print_function
import argparse
import os

from ffprobe_parser import *
from mp4dump_parser import *
from models import *

import plotly
import plotly.graph_objs as go
import pandas as pd
import scipy
import pytz
import statistics


def test_pandas(frames):
    df = pd.DataFrame.from_records([f.to_dict() for f in frames], index='start_time')
    print(df)

def sec2ts(sec):
    return datetime.fromtimestamp(sec, tz=pytz.UTC)

def get_fragment_data_from_track(track, start_time=None, end_time=None):
    data = []

    fragments = track.fragments
    # No fragments?
    if len(fragments) == 0:
        return data

    if (start_time and end_time):
        fragments = list(filter(lambda f: f.start_time < end_time and f.end_time > start_time, fragments))

    frag_bar = go.Bar(
        x=[f.start_time for f in fragments],
        y=[f.size for f in fragments],
        text=[str(f.duration.total_seconds()) + "s" for f in fragments],
        width=[f.duration.total_seconds()*1000 for f in fragments],
        offset=0,
        name="Fragment",
        marker=dict(
            color="rgba(127,127,127,0.2)",
            line=dict(
                width=2,
                color="#444"
            )
        ),
        yaxis='y2',
        textposition='inside',
        hoverinfo="text",
        hovertext=[f.to_label() for f in fragments]
    )
    data.append(frag_bar)

    return data

def get_frame_data_from_stream(stream):
    bars = [
        dict(type=IFrame, color='#FFBB00', label='I-frame'),
        dict(type=IDRFrame, color='#FF0000', label='IDR frame'),
        dict(type=PFrame, color='#6AFA00', label='P-frame'),
        dict(type=BFrame, color='#1900FF', label='B-frame'),
    ]

    data = []

    # Bars for frames (per type)
    for b in bars:
        frames = stream.get_frames_for_type(b['type'], strict=True)

        d = go.Bar(
            x=[f.start_time for f in frames],
            y=[f.size for f in frames],
            text=["frame {}".format(f.position) for f in frames],
            width=[f.duration.total_seconds()*1000 for f in frames],
            offset=[0 for f in frames],
            name=b['label'],
            marker=dict(
                color=b['color']
            ),
            hoverinfo="x+y+text+name"
        )

        data.append(d)

    return data

def get_bitrate_data_from_stream(stream):
    # turn frames into a pandas DataFrame indexed on start time
    df = pd.DataFrame.from_records([f.to_dict() for f in stream.frames], index='start_time')

    data = []

    # Bitrate
    means_expanding = df['bitrate'] \
        .expanding() \
        .mean()

    bitrate_expanding = go.Scatter(
        x=means_expanding.index,
        y=means_expanding.values,
        name="bitrate <br>(cumul mean)",
        yaxis='y3',
        mode="lines",
        line=dict(
            width=2,
            color="#7842AB"
        ),
        hoverinfo="x+y",
        # stackgroup='bitrates',
        # legendgroup = "bitrates"
    )
    data.append(bitrate_expanding)


    means_rolling = df['bitrate'] \
        .rolling(window=int(stream.frame_rate),
                 win_type='triang',
                 center=True
                 ) \
        .mean()

    bitrate_rolling = go.Scatter(
        x=means_rolling.index,
        y=means_rolling.values,
        name="bitrate <br>(MGB2 - 1s triang)",
        yaxis='y3',
        mode="lines",
        line=dict(
            width=1,
            color="#9467BD"
        ),
        hoverinfo="x+y",
        fill="tonexty",
        fillcolor="rgba(225,213,246,0.4)"
        # stackgroup='bitrates'
        # legendgroup="bitrates",
    )
    data.append(bitrate_rolling)



    return data

def get_gop_data_from_stream(stream):
    data = []
    gops = stream.gops

    bars = [
        dict(closed=True, color='rgb(235, 188, 188)', label='Closed GOP'),
        dict(closed=False, color='rgb(234, 220, 190)', label='Open GOP'),
    ]

    for bar in bars:
        # Bars for GOPs
        goplist = list(filter(lambda g: g.closed == bar['closed'], gops))
        gop_bar = go.Bar(
            x=[gop.start_time for gop in goplist],
            y=[gop.size for gop in goplist],
            text=[gop.length for gop in goplist],
            width=[gop.duration.total_seconds()*1000 for gop in goplist],
            offset=0,
            name=bar['label'],
            marker=dict(
                color=bar['color'],
                line=dict(
                    width=1,
                    color="#111111"
                )
            ),
            yaxis='y2',
            textposition='auto',
            hoverinfo="text",
            hovertext=[gop.to_label() for gop in stream.gops],
            legendgroup='gops'
        )
        data.append(gop_bar)

    return data


def plot_data(data, file, title, stream_label, track_label):
    filename = os.path.basename(args.path_to_file)

    layout = go.Layout(
        title="{}<br>{}".format(title, filename),
        xaxis=dict(
            title='',
            tickmode='auto',
            ticks='outside',
            showticklabels=True,
            dtick=1,
            tickformat="%X.%2f",
            tickfont=dict(
                size=12,
                color='rgb(107, 107, 107)'
            ),
            range=[
                stream.frames[0].start_time,
                stream.frames[-1].end_time
            ]
        ),
        yaxis=dict(
            domain=[0.30, 1],
            title='frame size (b)',
            titlefont=dict(
                size=16,
                color='rgb(107, 107, 107)'
            ),
            tickfont=dict(
                size=14,
                color='rgb(107, 107, 107)'
            ),
            fixedrange=True,
            hoverformat='.3s'
        ),
        yaxis2=dict(
            domain=[0, 0.25],
            title='size (b)',
            side='left',
            showticklabels=True,
            showgrid=False,
            anchor='x',
            spikesnap="data",
            spikemode="toaxis+across+marker",
            spikethickness=1,
            spikedash='dot',
            fixedrange=True
        ),
        yaxis3=dict(
            domain=[0.30, 1],
            title='bitrate (bps)',
            side='right',
            showticklabels=True,
            ticks='outside',
            showgrid=False,
            anchor='x',
            overlaying='y',
            showspikes=True,
            spikesnap="data",
            spikemode="toaxis+across+marker",
            spikethickness=1,
            spikedash='dot',
            fixedrange=False,
            hoverformat='.3s'
        ),
        legend=dict(
            x=1.06,
            traceorder="normal"
        ),
        annotations=[
            dict(
                x=1.03,
                y=0.3,
                xref='paper',
                yref='paper',
                xanchor='left',
                yanchor='bottom',
                xshift=0,
                yshift=0,
                showarrow=False,
                text=stream_label,
                borderpad=1,
                bgcolor="#F5FFFA",
                bordercolor="#d2cdcd",
                borderwidth=1,
                align="left"
            ),
            dict(
                x=1.03,
                y=0.20,
                xref='paper',
                yref='paper',
                xanchor='left',
                yanchor='top',
                xshift=0,
                yshift=0,
                showarrow=False,
                text=track_label,
                borderpad=1,
                bgcolor="#F0FFFF",
                bordercolor="#d2cdcd",
                borderwidth=1,
                align="left"
            )
        ],
    )

    plotly.offline.plot({
        "data": data,
        "layout": layout
    }, auto_open=True, filename="{}.html".format(file))


if __name__ == "__main__":
    print(os.environ['PATH'])

    parser = argparse.ArgumentParser(description='Dump GOP structure of video file')
    parser.add_argument('path_to_file', help='video file to parse')
    parser.add_argument('--ffprobe-exec', dest='ffprobe_exec',
                        help='ffprobe executable. (default: %(default)s)',
                        default='ffprobe')
    parser.add_argument('--mp4dump-exec', dest='mp4dump_exec',
                        help='mp4dump executable. (default: %(default)s)',
                        default='mp4dump')
    parser.add_argument('--intervals', dest='intervals',
                        help='interval to read from video file (see ffprobe -read_intervals parameter)')
    parser.add_argument('--streams', dest='streams',
                        help='streams to read from video file (see ffprobe -select_streams parameter)',
                        default='v:0')
    parser.add_argument('-t', '--title', dest='title',
                        help='Frame, GOP and Fragments Analysis (vviz.py)',
                        default='v:0')
    args = parser.parse_args()

    filename = os.path.basename(args.path_to_file)

    interval = args.intervals if args.intervals else None
    ffprobe = FFProbeCommand(executable=args.ffprobe_exec,
                             filename=args.path_to_file,
                             intervals=interval,
                             streams=args.streams)
    fresponse = ffprobe.call()

    stream = Stream(origin=fresponse, stream_index=0)

    mp4dump = MP4DumpCommand(executable=args.mp4dump_exec,
                             filename=args.path_to_file)
    mresponse = mp4dump.call()

    track = MP4Track(parser=mresponse)

    # test_pandas(stream.frames)

    data = []
    data += get_frame_data_from_stream(stream)
    data += get_bitrate_data_from_stream(stream)
    # filtering necessary as mp4dump does not offer command line parameters for it
    if (interval):
        data += get_fragment_data_from_track(track,
                                             start_time=stream.frames[0].start_time,
                                             end_time=stream.frames[-1].end_time)
    else:
        data += get_fragment_data_from_track(track)
    data += get_gop_data_from_stream(stream)

    plot_data(data, args.path_to_file, title=args.title, stream_label=stream.to_label(), track_label=track.to_label())