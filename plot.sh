#!/bin/env bash

function prepare {
    if docker image inspect haura_plots
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
}

export ROOT=$PWD

prepare

for run in "$1"/*
do
    plot "$run"
done
