#!/usr/bin/env bash

docker pull shilad/cartograph-base:latest &&
docker run \
    -e PYTHONPATH=. \
    -v "$(pwd)":/cartograph \
    -w /cartograph \
    -p 4000:4000 \
    shilad/cartograph-base:latest \
    python2.7 ./cartograph/server/app2.py $@