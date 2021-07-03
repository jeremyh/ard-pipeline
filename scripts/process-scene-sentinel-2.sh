#!/bin/bash

##############################################################################
#                                                                            #
# Script configures the existing docker environment for a execution of WAGL. #
#                                                                            #
# Usage ./process-scene.sh {{GRANULE_URL}} {{DATASTRIP_URL}} {{TASK_UUID}}   #
#                                                                            #
##############################################################################

# $0: process-scene.sh
# $1: $GRANULE_URL: Url to fetch the granule data from
# $2: $DATASTRIP_URL: Url to fetch the datastrip data from
# $3: $TASK_UUID: Unique identifier for the task
# $4: $S3_REGION: Region that the packaged content will be uploaded to
# $5: $S3_INPUT_PREFIX: s3://bucket/prefix that will serve as the root for uploaded content
# $6: $LUIGI_CONFIG_PATH: Which luigi config to use

# Command line args
GRANULE_URL="$1"
DATASTRIP_URL="$2"
TASK_UUID="$3"
S3_REGION="$4"
S3_INPUT_PREFIX="$5"
export LUIGI_CONFIG_PATH="/scripts/luigi-sentinel-2.cfg"

# separate s3://bucket_name/prefix into bucket_name prefix
read S3_BUCKET S3_BUCKET_PREFIX <<< $(echo "$S3_INPUT_PREFIX" | perl -pe's/s3:\/\/([^\/]+)\/(.*)/\1 \2/;')

WORKDIR="/granules"
OUTDIR="/output"
PKGDIR="/upload"

MOD6=/ancillary/MODTRAN6.0.2.3G/bin/linux/mod6c_cons

LOG_DEBUG=1
LOG_INFO=10
LOG_WARN=100
LOG_ERROR=1000
LOG_LEVEL=$LOG_DEBUG

EXIT_CODE=0

# Logging interface similar to python logging
function log_message {
    _LOG_LEVEL="$1"
    _LOG_MSG="$2"
    if [ $_LOG_LEVEL -ge $LOG_LEVEL ]; then
        echo "$_LOG_MSG"
    fi

    return 0;
}

# When the instance is initially launched some ancillary has to be updated
# This function waits for the ancillary data to complete syncing
# Assumption is made that the instance will have sufficient time to create
# the lockfile prior to the container initialising for the first time
function wait_for_ancillary {
    WAITING_FOR=0
    TIMEOUT_SECONDS=600
    while [[ -f "/ancillary/ancillary-fetch.lock" ]]; do
        if [ $WAITING_FOR -gt $TIMEOUT_SECONDS ]; then
            exit 124;
        fi
        WAITING_FOR=$(($WAITING_FOR+2))
        sleep 2
    done;

    return 0;
}

log_message $LOG_INFO "$0 called with $GRANULE_URL $DATASTRIP_URL $TASK_UUID $S3_REGION $S3_INPUT_PREFIX"
log_message $LOG_INFO "[s3 config] BUCKET:'$S3_BUCKET' PREFIX:'$S3_BUCKET_PREFIX'"
umask 000  # Safe guard against ancillary files locked to a specific container

mkdir -p $WORKDIR

log_message $LOG_INFO "Syncing tile information from s3"
# Sync data for the current granule
aws s3 sync --only-show-errors "$GRANULE_URL" "$WORKDIR/$TASK_UUID"
if [ "$?" -ne 0 ]; then
    log_message $LOG_ERROR "Unable to fetch granule";
    exit -1;
fi
log_message $LOG_INFO "Tile synched"

aws s3 sync --only-show-errors "$DATASTRIP_URL" "$WORKDIR/$TASK_UUID/datastrip"
if [ "$?" -ne 0 ]; then
    log_message $LOG_ERROR "Unable to fetch metadata";
    exit -1;
fi
log_message $LOG_INFO "Metadata synched"

# Create work file
echo "$WORKDIR/$TASK_UUID" > "$WORKDIR/$TASK_UUID/scenes.txt"

# Check if output already exists
python /scripts/check-exists.py --level1-path="$WORKDIR/$TASK_UUID" --acq-parser-hint="s2_sinergise" --s3-bucket="$S3_BUCKET" --s3-prefix="$S3_BUCKET_PREFIX"
if [ "$?" -ne 0 ]; then
    log_message $LOG_INFO "Output already exists, passing {} to XCom"
    mkdir -p /airflow/xcom/
    echo "{}" > /airflow/xcom/return.json
    exit 0;
fi

log_message $LOG_INFO "Waiting for ancillary to become ready"
wait_for_ancillary
log_message $LOG_INFO "Ancillary ready"

# Config files for wagl/luigi default to the current directory
# The Dockerfile moves the configs to the script folder
cd /scripts

# Generate the index yaml for the level 1c product
# Note that argument refers to a filename and not a directory
log_message $LOG_INFO "Generating 1C product metadata"
python s2-l1c-aws-pds-generate-metadata.py --output "$WORKDIR/$TASK_UUID" "$WORKDIR/$TASK_UUID"
CAPTURE_DATE="$(date -u --date=$(cat "$WORKDIR/$TASK_UUID/productInfo.json" | jq -r '.tiles[0].timestamp') '+%Y-%m-%d')"
log_message $LOG_INFO "Generated 1C product metadata"
log_message $LOG_INFO "CAPTURE_DATE=$CAPTURE_DATE"

# activate modtran6 license
log_message $LOG_INFO "Activating MODTRAN6"
$MOD6 -version
$MOD6 -activate_license $MODTRAN_PRODUCT_KEY

log_message $LOG_INFO "Running WAGL"

mkdir -p "$OUTDIR/$TASK_UUID"
mkdir -p "$PKGDIR/$TASK_UUID"

luigi --module tesp.workflow ARDP \
    --level1-list "$WORKDIR/$TASK_UUID/scenes.txt" \
    --workdir "$OUTDIR/$TASK_UUID" \
    --pkgdir "$PKGDIR/$TASK_UUID" \
    --acq-parser-hint s2_sinergise \
    --local-scheduler \
    --workers 1

if [ "$?" -ne 0 ]; then
    log_message $LOG_ERROR "Luigi failed: status-log.jsonl"
    while IFS='' read -r line || [[ -n "$line" ]];
    do
        log_message $LOG_ERROR "$line"
    done < "status-log.jsonl"

    log_message $LOG_ERROR "Luigi failed: task-log.jsonl"
    while IFS='' read -r line || [[ -n "$line" ]];
    do
        log_message $LOG_ERROR "$line"
    done < "task-log.jsonl"

    log_message $LOG_ERROR "Luigi failed: luigi-interface.log"
    while IFS='' read -r line || [[ -n "$line" ]];
    do
        log_message $LOG_ERROR "$line"
    done < "luigi-interface.log"

    # Cleanup
    log_message $LOG_INFO "Processing failed, remove working directories";
    rm -rf "$WORKDIR/$TASK_UUID"
    rm -f "$WORKDIR/$TASK_UUID.yaml"
    rm -rf "$PKGDIR/$TASK_UUID"
    rm -rf "$OUTDIR/$TASK_UUID"
    log_message $LOG_INFO "Cleanup complete";
    exit -1;
fi

cat luigi-interface.log status-log.jsonl task-log.jsonl

log_message $LOG_INFO "Remove working directories"

# Remove referenced data ahead of time since the docker orchestrator may be
# delayed in freeing up storage for re-use
rm -rf "$WORKDIR/$TASK_UUID"
rm -f "$WORKDIR/$TASK_UUID.yaml"
log_message $LOG_INFO "Working directories removed"

# upload to destination
log_message $LOG_INFO "Copying to destination"
aws s3 cp --recursive --only-show-errors --acl bucket-owner-full-control "$PKGDIR/$TASK_UUID" "${S3_INPUT_PREFIX}"
find "$PKGDIR/$TASK_UUID" -type f -printf '%P\n' | xargs -n 1 -I {} aws s3api put-object-tagging --bucket "${S3_BUCKET}" --tagging 'TagSet=[{Key=pipeline,Value="NRT Processing"},{Key=target_data,Value="Sentinel2 NRT"},{Key=remote_host,Value="AWS PDS Europe"},{Key=transfer_method,Value="Public Internet Fetch"},{Key=input_data,Value="Sentinel2 L1C"},{Key=input_data_type,Value="JP2000"},{Key=egress_location,Value="ap-southeast-2"},{Key=egress_method,Value="s3 upload"},{Key=archive_time,Value="30 days"},{Key=orchestrator,Value="airflow"}]' --key "${S3_BUCKET_PREFIX}"{}
log_message $LOG_INFO "Synch to destination complete"

# pass the location of the dataset to airflow xcom
log_message $LOG_INFO "Passing XCom"
mkdir -p /airflow/xcom/
pushd "$PKGDIR/$TASK_UUID/"
echo "{\"dataset\": \"${S3_INPUT_PREFIX}$(find . -type f -name 'ARD-METADATA.yaml' -printf '%P')\"}" > /airflow/xcom/return.json
popd

rm -rf "$PKGDIR/$TASK_UUID"
rm -rf "$OUTDIR/$TASK_UUID"

log_message $LOG_INFO "Complete"
log_message $LOG_INFO "Exiting with exit code ${EXIT_CODE}"
exit ${EXIT_CODE};
