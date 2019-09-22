#! /usr/bin/env bash

set -x
./user_downloader.py
./channel_downloader.py
./message_downloader.py
./automated_user_report
./slack_report.py --destination \#zmeta-statistics
set +x
