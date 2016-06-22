#!/bin/bash

DATA_DEST=data/labdata
DATA_SRC=labdata@como.macalester.edu/data

function die() {
    echo $@ >&2
    exit 1
}

if ! [ -f data/labdata.key ]; then
    die "Please download Summer2016/Downloads/labdata.key in Google Drive and place it in the $DATA directory."
fi

command=""
targets=""

if [ $# == 0 ]; then
	command=pull
	target=all
elif [ $# != 2 ]; then
	command="$1"
	target="$2"
else
	die "usage: $0 {push|pull} filename"
fi

if [ $command -eq "pull"]; then
	if [ targets -eq "all" ]; then
		srcs='*'
	else
		srcs="$DATA_SRC/$targets"
	fi
	rsync -avz "${srcs}" ${DATA_DEST}
elif [ $command -eq "push" ]; then
	if ! [ -f $DATA_DEST/labdata.key ];
else
fi
