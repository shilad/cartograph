#!/usr/bin/env bash

# This is run from the root directory, even though it appears here.
# All tests run from Travis should appear here.

# Clear everything out (somewhat carefully)
rm -rf ./data/ext/test/*sample*
rm -rf ./data/test/*
rm -rf ./data/integration_test/*
rm -rf ./data/test-orig/*/

# Run
./bin/docker-luigi.sh  --conf ./data/conf/integration_test.txt && \
dirs=$(find ./data/integration_test/* -type d -print) && \
cp -rp $dirs ./data/test-orig/  || \
    { echo "Creating test data failed!" >&2; exit 1; }

