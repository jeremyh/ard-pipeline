LOG_DEBUG=1
LOG_INFO=10
LOG_WARN=100
LOG_ERROR=1000

# Logging interface similar to python logging
function log_message {
    if [ "$1" -ge $LOG_LEVEL ]; then
        echo "$2"
    fi
}

# Log contents of a stream
function log_stream {
    while IFS='' read -r line || [[ -n "$line" ]];
    do
        log_message "$1" "$line"
    done
}

# Create task-specific folders
function create_task_folders {
    mkdir -p "$WORKDIR/$TASK_UUID"
    mkdir -p "$OUTDIR/$TASK_UUID"
    mkdir -p "$PKGDIR/$TASK_UUID"
}

# Fetch Landsat granule from S3 bucket
function fetch_landsat_granule {
    log_message $LOG_INFO "Fetching scene from s3"
    aws s3 sync --only-show-errors "$L1_BUCKET/$L1_PREFIX" "$WORKDIR/$TASK_UUID"
    if [ "$?" -ne 0 ]; then
        log_message $LOG_ERROR "Unable to fetch scene";
        exit -1;
    fi
    log_message $LOG_INFO "Fetching scene completed."
}

# Fetch Sentinel-2 granule from S3 bucket
function fetch_sentinel2_granule {
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
}

# Run luigi task ARDP
function run_luigi {
    log_message $LOG_INFO "Running luigi"
    luigi --module tesp.workflow ARDP \
        --level1-list "$WORKDIR/$TASK_UUID/scenes.txt" \
        --workdir "$OUTDIR/$TASK_UUID" \
        --pkgdir "$PKGDIR/$TASK_UUID" \
        --local-scheduler \
        --workers 1

    if [ "$?" -ne 0 ]; then
        log_message $LOG_ERROR "Luigi failed: status-log.jsonl"
        log_stream $LOG_ERROR < "status-log.jsonl"

        log_message $LOG_ERROR "Luigi failed: task-log.jsonl"
        log_stream $LOG_ERROR < "task-log.jsonl"

        log_message $LOG_ERROR "Luigi failed: luigi-interface.log"
        log_stream $LOG_ERROR < "luigi-interface.log"

        # Cleanup
        log_message $LOG_INFO "Processing failed, remove working directories";
        rm -rf "$WORKDIR/$TASK_UUID"
        rm -rf "$PKGDIR/$TASK_UUID"
        rm -rf "$OUTDIR/$TASK_UUID"
        log_message $LOG_INFO "Cleanup complete";
        exit -1;
    fi
}

# Activate modtran6 license
function activate_modtran {
    log_message $LOG_INFO "Activating MODTRAN6"
    $MOD6 -version
    $MOD6 -activate_license $MODTRAN_PRODUCT_KEY
}

# Check if output already exists for sentinel-2
function check_output_exists_sentinel2 {
    python /scripts/check-exists.py --level1-path="$WORKDIR/$TASK_UUID" --acq-parser-hint="s2_sinergise" --s3-bucket="$DESINATION_BUCKET" --s3-prefix="$DESINATION_PREFIX"
    if [ "$?" -ne 0 ]; then
        log_message $LOG_INFO "Output already exists, exiting."
        exit 0;
    fi
}

# Check if output already exists for landsat
function check_output_exists_landsat {
    python /scripts/check-exists.py --level1-path="$WORKDIR/$TASK_UUID" --s3-bucket="$DESINATION_BUCKET" --s3-prefix="$DESINATION_PREFIX"
    if [ "$?" -ne 0 ]; then
        log_message $LOG_INFO "Output already exists, exiting."
        exit 0;
    fi
}

# Receive message from queue for Landsat
function receive_message_landsat {
    aws sqs receive-message --queue-url="$SQS_QUEUE" --visibility-timeout="$ESTIMATED_COMPLETION_TIME" --max-number-of-messages=1 > "$WORKDIR/message.json" 2> "$WORKDIR/message.err"
    if [ "$?" -ne 0 ]; then
        log_message $LOG_ERROR "Could not receive message from ${SQS_QUEUE}"
        log_stream $LOG_ERROR < "$WORKDIR/message.err"
        exit -1;
    else
        log_message $LOG_DEBUG "Received message from ${SQS_QUEUE}"
        log_stream $LOG_DEBUG < "$WORKDIR/message.json"
    fi

    # Extract the task from the message
    jq -r '.Messages[0].Body' "$WORKDIR/message.json" | jq -r '.Message' > "$WORKDIR/task.json"
}

# Receive message from queue for Sentinel-2
function receive_message_sentinel2 {
    aws sqs receive-message --queue-url="$SQS_QUEUE" --visibility-timeout="$ESTIMATED_COMPLETION_TIME" --max-number-of-messages=1 > "$WORKDIR/message.json" 2> "$WORKDIR/message.err"
    if [ "$?" -ne 0 ]; then
        log_message $LOG_ERROR "Could not receive message from ${SQS_QUEUE}"
        log_stream $LOG_ERROR < "$WORKDIR/message.err"
        exit -1;
    else
        log_message $LOG_DEBUG "Received message from ${SQS_QUEUE}"
        log_stream $LOG_DEBUG < "$WORKDIR/message.json"
    fi

    # Extract the task from the message
    jq -r '.Messages[0].Body' "$WORKDIR/message.json" | jq -r '.Message' > "$WORKDIR/task.json"
}

# Prepare level-1 dataset yaml for sentinel-2
function prepare_level1_sentinel_2 {
# Note that argument refers to a filename and not a directory
    log_message $LOG_INFO "Generating 1C product metadata"
    eo3-prepare sentinel-l1 "$WORKDIR/$TASK_UUID"
    CAPTURE_DATE="$(date -u --date=$(cat "$WORKDIR/$TASK_UUID/productInfo.json" | jq -r '.tiles[0].timestamp') '+%Y-%m-%d')"
    log_message $LOG_INFO "Generated 1C product metadata"
    log_message $LOG_INFO "CAPTURE_DATE=$CAPTURE_DATE"
}

# Prepare level-1 dataset yaml for landsat
function prepare_level1_landsat {
    log_message $LOG_INFO "Generating 1C product metadata"
    eo3-prepare landsat-l1 $WORKDIR/$TASK_UUID
    mv $WORKDIR/*.yaml $WORKDIR/$TASK_UUID
    log_message $LOG_INFO "Generated 1C product metadata"
}

function upload_sentinel2 {
    # upload to destination
    log_message $LOG_INFO "Copying to destination"
    aws s3 cp --recursive --only-show-errors --acl bucket-owner-full-control "$PKGDIR/$TASK_UUID" "${DESTINATION_S3_URL}"
    find "$PKGDIR/$TASK_UUID" -type f -printf '%P\n' | xargs -n 1 -I {} aws s3api put-object-tagging --bucket "${DESINATION_BUCKET}" --tagging 'TagSet=[{Key=pipeline,Value="NRT Processing"},{Key=target_data,Value="Sentinel2 NRT"},{Key=remote_host,Value="AWS PDS Europe"},{Key=transfer_method,Value="Public Internet Fetch"},{Key=input_data,Value="Sentinel2 L1C"},{Key=input_data_type,Value="JP2000"},{Key=egress_location,Value="ap-southeast-2"},{Key=egress_method,Value="s3 upload"},{Key=archive_time,Value="30 days"},{Key=orchestrator,Value="airflow"}]' --key "${DESINATION_PREFIX}"{}
    log_message $LOG_INFO "Synch to destination complete"
}

function upload_landsat {
    # upload to destination
    log_message $LOG_INFO "Copying to destination"
    aws s3 cp --recursive --only-show-errors --acl bucket-owner-full-control "$PKGDIR/$TASK_UUID" "${DESTINATION_S3_URL}"
    find "$PKGDIR/$TASK_UUID" -type f -printf '%P\n' | xargs -n 1 -I {} aws s3api put-object-tagging --bucket "${DESINATION_BUCKET}" --tagging 'TagSet=[{Key=pipeline,Value="NRT Processing"},{Key=target_data,Value="Landsat NRT"},{Key=remote_host,Value="USGS M2M API"},{Key=transfer_method,Value="Internet Transfer"},{Key=input_data,Value="Landsat L1RT"},{Key=input_data_type,Value="GeoTIFF"},{Key=egress_location,Value="ap-southeast-2"},{Key=egress_method,Value="s3 upload"},{Key=archive_time,Value="30 days"},{Key=orchestrator,Value="airflow"}]' --key "${DESINATION_PREFIX}"{}
    log_message $LOG_INFO "Synch to destination complete"
}

function remove_workdirs {
    log_message $LOG_INFO "Remove working directory"
    # Remove referenced data ahead of time since the docker orchestrator may be
    # delayed in freeing up storage for re-use
    rm -rf "$PKGDIR/$TASK_UUID"
    rm -rf "$OUTDIR/$TASK_UUID"
    rm -rf "$WORKDIR/$TASK_UUID"
    log_message $LOG_INFO "Working directory removed"
}

# Finish up script run
function finish_up {
    log_message $LOG_INFO "Complete"
    log_message $LOG_INFO "Exiting with exit code 0"
    exit 0;
}
