#!/usr/bin/env bash

docker pull shilad/cartograph-base:latest &&
docker run --env PYTHONPATH=. -v "$(pwd)":/cartograph -w /cartograph shilad/cartograph-base:latest $@
