#!/bin/bash

export PYTHONPATH=$PYTHONPATH:.:./cartograph

me=$0

SERVER_CONF=
MAP_CONF=
INPUT_FILE=

function usage() {
    echo "
    usage: $me {-h|--help}
            {--module ModuleName}
        {--task TaskName}
        {--server_conf ConfFile.txt}
        {--map_conf ConfFile.txt}
        {--input input-file.txt}
" >&2
    exit 1
}

function getMapConfSetting() {
    section=$1
    key=$2
    python2.7 ./cartograph/MapConfig.py "$MAP_CONF" $section $key || \
        { echo "getting $section $key in $MAP_CONF" failed >&2; exit 1; }
}

MODULE=cartograph
TASK=ParentTask
STATUSFILE=

while [ "$1" != "" ]; do
    case $1 in
        -h | --help)
            usage
            exit
            ;;
        --task)
            TASK=$2
            shift
            ;;
        --module)
            MODULE=$2
            shift
            ;;
        --server_conf)
            SERVER_CONF=$2
            shift
            ;;
        --map_conf)
            MAP_CONF=$2
            shift
            ;;
        --input)
            INPUT_FILE=$2
            shift
            ;;
        *)
            echo "ERROR: unknown parameter \"$1\""
            usage
            exit 1
            ;;
    esac
    shift
done


if [ -z "$MAP_CONF" ]; then
    echo "No map configuration specified" >&2
    usage
fi

if [ -n "$INPUT_FILE" ] && [ -z "$SERVER_CONF" ]; then
    echo "Input file specified without server configuration" >&2
    usage
fi

if [ -n "$SERVER_CONF" ] && [ -z "$INPUT_FILE" ]; then
    echo "Server configuration specified without input file" >&2
    usage
fi

if [ -n "$INPUT_FILE" ]; then
    docker run --env PYTHONPATH=. -v "$(pwd)":/cartograph -w /cartograph shilad/cartograph-base:latest /bin/bash -c \
	    "python ./cartograph/MakeInputs.py $SERVER_CONF $MAP_CONF $INPUT_FILE; ./bin/luigi.sh --conf $MAP_CONF"
fi


export CARTOGRAPH_CONF=$MAP_CONF

function updateStatus() {
    statusFile=$(getMapConfSetting DEFAULT externalDir)/status.txt
    echo $@ >$statusFile
}

updateStatus "RUNNING $$"
