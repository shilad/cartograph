#!/usr/bin/env bash

# This script publishes a new docker test image.
# You must have executed docker login successfully before running it.
#
#   Usage: publish.sh 0.0.1

export DOCKER_ID_USER="shilad"

USERNAME=$DOCKER_ID_USER
IMAGE=cartograph-integration

version=$1
if [ -z "$version" ]; then
    echo "usage: $0 version"
    exit 1
fi


docker build -t $IMAGE:latest . && \
docker run $IMAGE:latest && \
docker tag $IMAGE:latest $USERNAME/$IMAGE:$version && \
docker tag $IMAGE:latest $USERNAME/$IMAGE:latest && \
docker push $USERNAME/$IMAGE:latest && \
docker push $USERNAME/$IMAGE:$version && \
echo "SUCCESSFULLY PUSHED $USERNAME/$IMAGE:$version "
