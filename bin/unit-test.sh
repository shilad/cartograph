#!/usr/bin/env bash

# This is run from the root directory, even though it appears here.
# All tests run from Travis should appear here.

rm -rf ./cartograph/__pycache__/*-PYTEST.pyc
python2.7 -m pytest ./cartograph/*.py || { echo "UNIT TESTS FAILED!" >&2; exit 1; }