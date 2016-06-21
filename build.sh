#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.
if luigi --module workflow Embedding --local-scheduler; then
	echo "LUIGI BUILD SUCCEEDED" >&2
	exit 0
else
	echo "LUIGI BUILD FAILED" >&2
	exit 1
fi
