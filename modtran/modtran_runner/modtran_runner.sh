#!/bin/bash
export MOD6=/modtran6/bin/linux/mod6c_cons
$MOD6 -version
$MOD6 -activate_license $MODTRAN_PRODUCT_KEY

export OUTPUT_DIR=/tests/$HOSTNAME
mkdir -p $OUTPUT_DIR
cp /modtran_runner/test-input-data.json $OUTPUT_DIR
cd $OUTPUT_DIR
$MOD6 test-input-data.json
