#! /usr/bin/env bash

BASEDIR=$(dirname "$0")
cd $BASEDIR
git pull

set -x
./user_downloader.py
./channel_downloader.py
set +x
