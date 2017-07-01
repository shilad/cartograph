#!/usr/bin/env bash

docker pull shilad/cartograph-base:latest &&
docker run -v "$(pwd)":/cartograph -w /cartograph shilad/cartograph-base:latest /bin/bash -c "./bin/unit-test.sh && ./bin/integration-test.sh"