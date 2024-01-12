#!/bin/env bash

function plot {
    local run=$1
    shift 1

    poetry --directory=haura-plots run plots "$run"

    pushd "$run"
    if [ -e plot_timestep_000.png ]
    then
        ffmpeg -framerate 2 -i plot_timestep_%03d.png -c:v libx264 -pix_fmt yuv420p plot_timestep.mp4
    fi
    popd
}

export ROOT=$PWD

for run in "$1"/*
do
    plot "$run"
done
