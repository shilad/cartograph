#!/bin/bash

export PYTHONPATH=$PYTHONPATH:.:./cartograph

me=$0

CONF=conf.txt

function usage() {
    echo "usage: $me {-h|--help} {--module ModuleName} {--task TaskName} {--conf ConfFile.txt}" >&2
    exit 1
}

MODULE=RenderMap
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
        --module)
            MODULE=$2
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

if luigi --module $MODULE $TASK \
         --local-scheduler \
         --retcode-task-failed 1 \
         --logging-conf-file ./data/conf/logging.conf; then
	echo "LUIGI BUILD SUCCEEDED" >&2
	exit 0
else
	echo "LUIGI BUILD FAILED" >&2
	exit 1
fi
