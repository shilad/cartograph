#!/usr/bin/env bash

# This script publishes a new docker test image.
# You must have executed docker login successfully before running it.
#
#   Usage: publish.sh 0.0.1

export DOCKER_ID_USER="shilad"

USERNAME=$DOCKER_ID_USER
IMAGE_BASE=cartograph-base

version=$1
if [ -z "$version" ]; then
    echo "usage: $0 version"
    exit 1
fi

# Base image
cp -p requirements.txt ./docker/base && \
docker build --no-cache=true -t $IMAGE_BASE:latest ./docker/base && \
docker run $IMAGE_BASE:latest && \
docker tag $IMAGE_BASE:latest $USERNAME/$IMAGE_BASE:$version && \
docker tag $IMAGE_BASE:latest $USERNAME/$IMAGE_BASE:latest && \
docker push $USERNAME/$IMAGE_BASE:latest && \
docker push $USERNAME/$IMAGE_BASE:$version && \
echo "SUCCESSFULLY PUSHED $USERNAME/$IMAGE_BASE:$version "