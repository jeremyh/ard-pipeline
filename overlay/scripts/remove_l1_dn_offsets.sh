#!/bin/bash

set -euo pipefail

# Run either in the current directory, or within to the supplied directory
if [[ -v 1 ]]; then
    cd "$1"
fi

if [[ ! -r MTD_MSIL1C.xml ]]; then
    echo "Unable to find MTD_MSIL1C.xml, please supply a Sentinel 2 Level 1 dataset dir."
    exit 1
fi

if ! grep -q Radiometric_Offset_List MTD_MSIL1C.xml; then
    echo "No Radiometric Offsets found, SKIPPING."
    exit
fi


# User xmlstarlet to extract the filenames and data offsets
# shellcheck disable=SC2016
for op in $(xmlstarlet sel -t -m "//IMAGE_FILE" --var "band_id=position()-1" \
    --if '//RADIO_ADD_OFFSET[@band_id=$band_id]' \
    -v "." -o "," -v "//RADIO_ADD_OFFSET[@band_id=\$band_id]" -nl MTD_MSIL1C.xml); do
    
    fname=${op%,*}
    offset=${op#*,}

    echo "Applying Pixel Data Offset to ${fname}.jp2"

    echo Running gdal_calc.py -A "${fname}.jp2" --outfile=temp.tif --calc="numpy.where(A == 0, 0, A+${offset})"
    gdal_calc.py -A "${fname}.jp2" --outfile=temp.tif --calc="numpy.where(A == 0, 0, A+${offset})"
    echo Running gdal_translate -co QUALITY=100 -co REVERSIBLE=YES -co YCBCR420=NO temp.tif "${fname}.jp2"
    gdal_translate --config GDAL_PAM_ENABLED NO -co QUALITY=100 -co REVERSIBLE=YES -co YCBCR420=NO temp.tif "${fname}.jp2"
    rm -f temp.tif
done

# Use xmlstarlet again to delete the Radiometric Offset section
cp MTD_MSIL1C.xml MTD_MSIL1C.xml.orig
xmlstarlet ed --pf -d "//Radiometric_Offset_List" MTD_MSIL1C.xml.orig > MTD_MSIL1C.xml
