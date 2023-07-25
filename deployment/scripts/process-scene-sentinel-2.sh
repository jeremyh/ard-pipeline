#!/bin/bash

# $0: this script
# $1: $GRANULE_URL: URL to fetch the granule data from
# $2: $DATASTRIP_URL: URL to fetch the datastrip data from
# $3: $TASK_UUID: Unique identifier for the task
# $4: $DESTINATION_S3_URL: s3://bucket/prefix that will serve as the root for uploaded content
# $5: $SNS_TOPIC: URL to publish ODC metadata of the L2 dataset
# $6: $EXPLORER_URL: URL for destination STAC metadata

GRANULE_URL="$1"
DATASTRIP_URL="$2"
TASK_UUID="$3"
DESTINATION_S3_URL="$4"
SNS_TOPIC="$5"
EXPLORER_URL="$6"

WORKDIR="/granules"
OUTDIR="/output"
PKGDIR="/upload"
MOD6=/ancillary/MODTRAN6.0.2.3G/bin/linux/mod6c_cons
export LUIGI_CONFIG_PATH="/configs/sentinel-2.cfg"

# separate s3://bucket_name/prefix into bucket_name prefix
read DESTINATION_BUCKET DESTINATION_PREFIX <<< $(echo "$DESTINATION_S3_URL" | perl -pe's/s3:\/\/([^\/]+)\/(.*)/\1 \2/;')

source /scripts/lib.sh
LOG_LEVEL=$LOG_DEBUG

log_message $LOG_INFO "$0 called with $GRANULE_URL $DATASTRIP_URL $TASK_UUID $DESTINATION_S3_URL $SNS_TOPIC $EXPLORER_URL"
log_message $LOG_INFO "[s3 destination config] BUCKET:'$DESTINATION_BUCKET' PREFIX:'$DESTINATION_PREFIX'"

create_task_folders
fetch_sentinel2_granule

# Create work file
echo "$WORKDIR/$TASK_UUID" > "$WORKDIR/$TASK_UUID/scenes.txt"

prepare_level1_sentinel_2
check_output_exists

# Config files for wagl/luigi default to the current directory
# The Dockerfile moves the configs to the script folder
cd /scripts

activate_modtran
run_luigi

write_stac_metadata
upload_sentinel2

publish_sns
remove_workdirs

finish_up
