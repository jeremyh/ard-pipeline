#!/bin/bash
#
set -euo pipefail

UUID=$(cat /proc/sys/kernel/random/uuid)
export UUID

$MOD6 -version
$MOD6 -activate_license "${MODTRAN_PRODUCT_KEY}"

export OUTPUT_DIR=/tests/$UUID
mkdir -p "${OUTPUT_DIR}"
cp /modtran_runner/landsat8_vsir.flt /tests/
cp /modtran_runner/test-input-data.json "${OUTPUT_DIR}"
cd "${OUTPUT_DIR}"
$MOD6 test-input-data.json
find . -type f
