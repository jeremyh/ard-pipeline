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
export LUIGI_CONFIG_PATH="/scripts/luigi-landsat.cfg"

# separate s3://bucket_name/prefix into bucket_name prefix
read DESINATION_BUCKET DESINATION_PREFIX <<< $(echo "$DESTINATION_S3_URL" | perl -pe's/s3:\/\/([^\/]+)\/(.*)/\1 \2/;')

source /scripts/lib.sh
LOG_LEVEL=$LOG_DEBUG

log_message $LOG_INFO "$0 called with $SQS_QUEUE $SOURCE_BUCKET $DESTINATION_S3_URL $SNS_TOPIC"
log_message $LOG_INFO "[s3 destination config] BUCKET:'$DESINATION_BUCKET' PREFIX:'$DESINATION_PREFIX'"

# saves the message to $WORKDIR/task.json
receive_message_landsat

RECEIPT_HANDLE=$(jq -r '.Messages[0].ReceiptHandle' "$WORKDIR/message.json")
TASK_UUID=$(jq -r '.Messages[0].MessageId' "$WORKDIR/message.json")
L1_SUCCESS=$(jq -r '.success' "$WORKDIR/task.json")
L1_PREFIX=$(jq -r '.prefix' "$WORKDIR/task.json")
L1_BUCKET=$(jq -r '.bucket' "$WORKDIR/task.json")

log_message $LOG_INFO "RECEIPT_HANDLE=${RECEIPT_HANDLE}"
log_message $LOG_INFO "L1_SUCCESS=${L1_SUCCESS}"
log_message $LOG_INFO "L1_PREFIX=${L1_PREFIX}"
log_message $LOG_INFO "L1_BUCKET=${L1_BUCKET}"

create_task_folders
fetch_landsat_granule
check_output_exists_landsat

# Create work file
echo "$WORKDIR/$TASK_UUID" > "$WORKDIR/$TASK_UUID/scenes.txt"

prepare_level1_landsat

cd /scripts

activate_modtran
run_luigi
log_message $LOG_ERROR "Luigi succeeded: status-log.jsonl"
log_stream $LOG_ERROR < "status-log.jsonl"

log_message $LOG_ERROR "Luigi succeeded: task-log.jsonl"
log_stream $LOG_ERROR < "task-log.jsonl"

log_message $LOG_ERROR "Luigi succeeded: luigi-interface.log"
log_stream $LOG_ERROR < "luigi-interface.log"

upload_landsat
notify_sns
delete_message
remove_workdirs

# TO DO
# SNS notification
# delete SQS message

finish_up
