#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.

command=""

if [ $# == 0 ]; then
	command="RenderMap"
elif [ $# == 1 ]; then
	command="$1"
fi

if luigi --module workflow $command --local-scheduler --retcode-task-failed 1; then
	echo "LUIGI BUILD SUCCEEDED" >&2
	exit 0
else
	echo "LUIGI BUILD FAILED" >&2
	exit 1
fi
