#!/bin/env bash

function plot {
    local run=$1
    shift 1

    docker run -v "$PWD":/usr/src/bench -w /usr/src/bench amancevice/pandas:1.4.3-alpine python jupyter/plot.py "$run"
}

export ROOT=$PWD

for run in "$1"/*
do
    plot "$run"
done
