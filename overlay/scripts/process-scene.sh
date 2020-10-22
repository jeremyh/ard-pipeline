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

# Command line args
GRANULE_URL="$1"
DATASTRIP_URL="$2"
TASK_UUID="$3"
S3_REGION="$4"
S3_INPUT_PREFIX="$5"

# separate s3://bucket_name/prefix into bucket_name prefix
read S3_BUCKET S3_BUCKET_PREFIX <<< $(echo "$S3_INPUT_PREFIX" | perl -pe's/s3:\/\/([^\/]+)\/(.*)/\1 \2/;')

WORKDIR="/granules"
OUTDIR="/output"

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

# Activate Python environment
# environment contains references to aws cli
source activate wagl
if [ "$?" -ne 0 ]; then
    log_message $LOG_ERROR "Unable to find environment"
    exit -1;
fi

log_message $LOG_INFO "Syncing tile information from s3"
# Sync data for the current granule
aws s3 sync --only-show-errors "$GRANULE_URL" "$WORKDIR/$TASK_UUID"
if [ "$?" -ne 0 ]; then
    log_message $LOG_ERROR "Unable to fetch granule";
    exit -1;
fi

aws s3 sync --only-show-errors "$DATASTRIP_URL" "$WORKDIR/$TASK_UUID/datastrip"
if [ "$?" -ne 0 ]; then
    log_message $LOG_ERROR "Unable to fetch metadata";
    exit -1;
fi

log_message $LOG_INFO "Adding user to /etc/passwd"

# Create work file
echo "$WORKDIR/$TASK_UUID" > "$WORKDIR/$TASK_UUID/scenes.txt"

log_message $LOG_INFO "Waiting for ancillary to become ready"
wait_for_ancillary

# Config files for wagl/luigi default to the current directory
# The Dockerfile moves the configs to the script folder
cd /scripts

# Generate the index yaml for the level 1c product
# Note that argument refers to a filename and not a directory
python3 s2_l1c_aws_pds_generate_metadata.py --output "$WORKDIR" "$WORKDIR/$TASK_UUID"
CAPTURE_DATE="$(date -u --date=$(cat "$WORKDIR/$TASK_UUID/productInfo.json" | jq -r '.tiles[0].timestamp') '+%Y-%m-%d')"

python3 /scripts/ancillary_fetch.py $CAPTURE_DATE --action water_vapour
python3 /scripts/ancillary_fetch.py $CAPTURE_DATE --action brdf

log_message $LOG_INFO "Running WAGL"

mkdir -p "$OUTDIR/upload"
mkdir -p "$OUTDIR/$TASK_UUID"

luigi --module tesp.workflow ARDP \
    --level1-list "$WORKDIR/$TASK_UUID/scenes.txt" \
    --workdir "$OUTDIR/$TASK_UUID" \
    --pkgdir "$OUTDIR/upload" \
    --acq-parser-hint s2_sinergise \
    --local-scheduler \
    --workers 1

if [ "$?" -ne 0 ]; then
    log_message $LOG_ERROR "Luigi failed: wagl-errors.log"
    while IFS='' read -r line || [[ -n "$line" ]];
    do
        log_message $LOG_ERROR "$line"
    done < "wagl-errors.log"

    log_message $LOG_ERROR "Luigi failed: wagl-status.log"
    while IFS='' read -r line || [[ -n "$line" ]];
    do
        log_message $LOG_ERROR "$line"
    done < "wagl-status.log"

    log_message $LOG_ERROR "Luigi failed: luigi-interface.log"
    while IFS='' read -r line || [[ -n "$line" ]];
    do
        log_message $LOG_ERROR "$line"
    done < "luigi-interface.log"

    EXIT_CODE=-1
fi

log_message $LOG_INFO "Remove working directories"

# Remove referenced data ahead of time since the docker orchestrator may be
# delayed in freeing up storage for re-use
rm -rf "$WORKDIR/$TASK_UUID"
rm "$WORKDIR/$TASK_UUID.yaml"

# upload to destination
aws s3 sync --only-show-errors "$OUTDIR/upload" "${S3_INPUT_PREFIX}"

log_message $LOG_INFO "Complete"
exit ${EXIT_CODE};
