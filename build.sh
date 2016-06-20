#!/bin/bash

if luigi --module workflow WikiBrain --local-scheduler; then
	echo "LUIGI BUILD SUCCEEDED" >&2
	exit 0
else
	echo "LUIGI BUILD FAILED" >&2
	exit 1
fi
