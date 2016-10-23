#!/usr/bin/env bash

if [ "$#" -ne 1 ]; then
    echo "usage: $0 path/to/carto_conf.txt"
    exit 1
fi

export CARTOGRAPH_CONFIG=$1
export PYTHONPATH=$PYTHONPATH:.

echo "Starting server" >&2
gunicorn cartograph.server.app:app -w 14 --max-requests 1000 --preload -b 127.0.0.1:4000

