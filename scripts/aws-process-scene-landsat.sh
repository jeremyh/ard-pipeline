#!/bin/bash

# $0: this script
# $1: $SQS_QUEUE: URL of the SQS queue to fetch task from
# $2: $SOURCE_BUCKET: URL of the source bucket for L1 data
# $3: $DESINATION_S3_URL: URL of the destination of the L2 data
# $4: $SNS_TOPIC: URL to publish ODC metadata of the L2 dataset

SQS_QUEUE="$1"
SOURCE_BUCKET="$2"
DESTINATION_S3_URL="$3"
SNS_TOPIC="$4"

ESTIMATED_COMPLETION_TIME=10800   # 3 hours
WORKDIR="/granules"
OUTDIR="/output"
PKGDIR="/upload"
MOD6=/ancillary/MODTRAN6.0.2.3G/bin/linux/mod6c_cons
LUIGI_CONFIG_PATH="/scripts/luigi-landsat.cfg"

# separate s3://bucket_name/prefix into bucket_name prefix
read DESINATION_BUCKET DESINATION_PREFIX <<< $(echo "$DESTINATION_S3_URL" | perl -pe's/s3:\/\/([^\/]+)\/(.*)/\1 \2/;')

source /scripts/lib.sh
LOG_LEVEL=$LOG_DEBUG

log_message $LOG_INFO "$0 called with $SQS_QUEUE $SOURCE_BUCKET $DESINATION_S3_URL $SNS_TOPIC"
log_message $LOG_INFO "[s3 destination config] BUCKET:'$DESINATION_BUCKET' PREFIX:'$DESINATION_PREFIX'"

# saves the message to $WORKDIR/task.json
receive_message_landsat

L1_SUCCESS=$(jq -r '.success')
L1_PREFIX=$(jq -r '.prefix')
L1_BUCKET=$(jq -r '.bucket')

log_message $LOG_INFO "L1_SUCCESS=${L1_SUCCESS}"
log_message $LOG_INFO "L1_PREFIX=${L1_PREFIX}"
log_message $LOG_INFO "L1_BUCKET=${L1_BUCKET}"

echo "bailing"
exit -1;

create_task_folders
fetch_landsat_granule
check_output_exists

# Create work file
echo "$WORKDIR/$TASK_UUID" > "$WORKDIR/$TASK_UUID/scenes.txt"

prepare_level1_landsat

cd /scripts

activate_modtran
run_luigi

upload_landsat
remove_workdir

# TO DO
# SNS notification
# delete SQS message

finish_up
