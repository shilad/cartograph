#!/usr/bin/env bash

# This is run from the root directory, even though it appears here.
# All tests run from Travis should appear here.

rm -rf ./data/ext/test/*sample*
rm -rf ./data/test/*
./bin/docker-luigi.sh  --conf ./data/conf/integration_test.txt