#!/bin/bash

# $0: this script
# $1: $SQS_QUEUE: URL of the SQS queue to fetch task from
# $2: $DESTINATION_S3_URL: URL of the destination of the L2 data
# $3: $SNS_TOPIC: URL to publish ODC metadata of the L2 dataset
# $4: $EXPLORER_URL: URL for destination STAC metadata

SQS_QUEUE="$1"
DESTINATION_S3_URL="$2"
SNS_TOPIC="$3"
EXPLORER_URL="$4"

ESTIMATED_COMPLETION_TIME=10800   # 3 hours
WORKDIR="/granules"
OUTDIR="/output"
PKGDIR="/upload"
MOD6=/ancillary/MODTRAN6.0.2.3G/bin/linux/mod6c_cons
export LUIGI_CONFIG_PATH="/configs/landsat.cfg"

# separate s3://bucket_name/prefix into bucket_name prefix
read DESTINATION_BUCKET DESTINATION_PREFIX <<< $(echo "$DESTINATION_S3_URL" | perl -pe's/s3:\/\/([^\/]+)\/(.*)/\1 \2/;')

source /scripts/lib.sh
LOG_LEVEL=$LOG_DEBUG

log_message $LOG_INFO "$0 called with $SQS_QUEUE $DESTINATION_S3_URL $SNS_TOPIC $EXPLORER_URL"
log_message $LOG_INFO "[s3 destination config] BUCKET:'$DESTINATION_BUCKET' PREFIX:'$DESTINATION_PREFIX'"

# saves the message to $WORKDIR/message.json and the body to $WORKDIR/task.json
receive_message_landsat

RECEIPT_HANDLE=$(jq -r '.Messages[0].ReceiptHandle' "$WORKDIR/message.json")
TASK_UUID=$(jq -r '.Messages[0].MessageId' "$WORKDIR/message.json")
L1_SUCCESS=$(jq -r '.success' "$WORKDIR/task.json")
L1_PREFIX=$(jq -r '.prefix' "$WORKDIR/task.json")
L1_BUCKET=$(jq -r '.bucket' "$WORKDIR/task.json")

if [[ "$L1_SUCCESS" != "true" ]]; then
    log_message $LOG_INFO "Level-1 data download was not successful, nothing to do!"
    exit 0;
fi

log_message $LOG_INFO "RECEIPT_HANDLE=${RECEIPT_HANDLE}"
log_message $LOG_INFO "L1_SUCCESS=${L1_SUCCESS}"
log_message $LOG_INFO "L1_PREFIX=${L1_PREFIX}"
log_message $LOG_INFO "L1_BUCKET=${L1_BUCKET}"

create_task_folders
fetch_landsat_granule
check_output_exists

# Create work file
echo "$WORKDIR/$TASK_UUID" > "$WORKDIR/$TASK_UUID/scenes.txt"

prepare_level1_landsat

cd /scripts

activate_modtran
run_luigi

write_stac_metadata
upload_landsat
delete_message
publish_sns
remove_workdirs

finish_up
