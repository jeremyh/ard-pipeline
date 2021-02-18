#!/bin/bash
export MOD6=/modtran6/bin/linux/mod6c_cons
$MOD6 -version
$MOD6 -activate_license $MODTRAN_PRODUCT_KEY

cp /modtran_runner/test-input-data.json /tests/
cd /tests/
$MOD6 test-input-data.json
