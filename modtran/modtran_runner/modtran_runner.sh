#!/bin/bash
echo "This is the modtran runner starting!"
echo $MODTRAN_DATA
echo $MODTRAN_PRODUCT_KEY
cp /modtran_runner/test-input-data.json /tests/
/modtran6/bin/linux/mod6c_cons -version
/modtran6/bin/linux/mod6c_cons -activate_license $MODTRAN_PRODUCT_KEY
cd /tests/
/modtran6/bin/linux/mod6c_cons test-input-data.json
echo "modtran runner ending"
