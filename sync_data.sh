#!/bin/bash
#
# A script to push or pull big data files against the server.
#
# Usage:
#
#   ./sync_data.sh                  # pulls all remote files to local system
#   ./sync_data.sh pull filename    # pulls a specific remote file onto local system
#   ./sync_data.sh push filename    # pulls a specific local file to remote system
#
# Files will reside in local directory data/labdata/.
# 
#
#

KEYFILE=data/labdata.key
DATA_LOCAL=data/labdata
HOST_REMOTE=labdata@como.macalester.edu
REMOTE_DIR=data
DATA_REMOTE=$HOST_REMOTE:$REMOTE_DIR

function do_rsync() {
    echo executing: rsync -avuz -e "ssh -i $KEYFILE" $@
    rsync -avz -e "ssh -i $KEYFILE" $@ || die "FAILURE!"
}

function do_ssh() {
    ssh -i $KEYFILE $HOST_REMOTE $@
}

function die() {
    echo $@ >&2
    exit 1
}


if ! [ -f $KEYFILE ]; then
    die "Please download Summer2016/Downloads/labdata.key in Google Drive and place it as $KEYFILE"
fi

chmod 600 $KEYFILE

command=""
targets=""

if [ $# == 0 ]; then
	command=pull
	target=all
elif [ $# == 2 ]; then
	command="$1"
	target="$2"
else
	die "usage: $0 {push|pull} filename"
fi

if [ $command == "pull" ]; then
	if [ targets == "all" ]; then
		srcs='*'
	else
		srcs="$DATA_REMOTE/$targets"
	fi
	do_rsync ${srcs} ${DATA_LOCAL}
elif [ $command == "push" ]; then
    src=""
    for s in "$target" "$DATA_LOCAL/$target"; do
        if [ -f "$s" ]; then
            src="$s"
            break
        fi
    done
    if [ -z "$src" ]; then
        die "couldn't find src file as either $target or $DATA_LOCAL/$target"
    fi
    prefix=
    if [[ $src =~ labdata ]]; then
        prefix=`dirname ${src/*labdata\//}`/
        do_ssh mkdir "$REMOTE_DIR/$prefix"
    fi 
	do_rsync ${src} ${DATA_REMOTE}/$prefix
else
    die "unknown command $command; usage $0 {push|pull} filename"
fi
