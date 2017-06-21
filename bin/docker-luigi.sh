#!/usr/bin/env bash

docker pull shilad/cartograph-base:latest &&
docker run -v "$(pwd)":/cartograph -w /cartograph shilad/cartograph-base:latest ./bin/luigi.sh $@