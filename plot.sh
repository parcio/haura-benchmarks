#!/bin/env bash

function prepare {
    if docker image inspect haura_plots > /dev/null 2>&1
    then
        return
    else
        docker build -t haura_plots .
    fi
}

function plot {
    local run=$1
    shift 1

    docker run -v "$PWD":/usr/src/bench -w /usr/src/bench haura_plots python jupyter/plot.py "$run"
    pushd "$run"
    if -e plot_timestep_000.png
    then
        ffmpeg -framerate 2 -i plot_timestep_%03d.png -c:v libx264 -pix_fmt yuv420p plot_timestep.mp4
    fi
    popd
}

export ROOT=$PWD

prepare

for run in "$1"/*
do
    plot "$run"
done
