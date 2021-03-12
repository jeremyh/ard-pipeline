#!/bin/bash
set -euo pipefail
export MOD6=/modtran6/MODTRAN6.0/bin/linux/mod6c_cons
export UUID=$(cat /proc/sys/kernel/random/uuid)
$MOD6 -version
$MOD6 -activate_license $MODTRAN_PRODUCT_KEY

export OUTPUT_DIR=/tests/$UUID
mkdir -p $OUTPUT_DIR
cp /modtran_runner/landsat8_vsir.flt /tests/
cp /modtran_runner/test2-input-data.json $OUTPUT_DIR
cd $OUTPUT_DIR
$MOD6 test2-input-data.json
if [ -v AWS_ACCESS_KEY_ID ]; then
    aws s3 sync . s3://dea-dev-eks-nrt-scene-cache/$UUID
fi
