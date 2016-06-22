#!/bin/bash

DATA=data

function die() {
    echo $@ >&2
    exit 1
}

if ! [ -f $DATA/labdata.key ]; then
    die "Please download Summer2016/Downloads/labdata.key in Google Drive and place it in the $DATA directory."
fi

command=""
targets=""

if [ $# == 0 ]; then
    echo "foo"
fi
