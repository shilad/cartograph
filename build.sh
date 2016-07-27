#!/bin/bash

export PYTHONPATH=$PYTHONPATH:.

me=$0

CONF=conf.txt

function usage() {
    echo "usage: $me {-h|--help} {--task TaskName} {--conf ConfFile.txt}" >&2
    exit 1
}

TASK=RenderMap

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
        --conf)
            CONF=$2
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

export CARTOGRAPH_CONF=$CONF

if luigi --module workflow $TASK \
         --local-scheduler \
         --retcode-task-failed 1 \
         --logging-conf-file ./data/conf/logging.conf; then
	echo "LUIGI BUILD SUCCEEDED" >&2
	exit 0
else
	echo "LUIGI BUILD FAILED" >&2
	exit 1
fi
