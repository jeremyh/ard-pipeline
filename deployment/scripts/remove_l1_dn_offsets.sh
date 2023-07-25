#!/bin/bash

cd "$1" || exit 1

if [[ ! -r l1c-metadata.xml ]]; then
    echo "Unable to find l1c-metadata.xml"
    exit
fi

if ! grep -q Radiometric_Offset_List l1c-metadata.xml; then
    echo "No Radiometric Offsets found, SKIPPING."
    exit
fi


# User xmlstarlet to extract the filenames and data offsets
# shellcheck disable=SC2016
for op in $(xmlstarlet sel -t -m "//IMAGE_FILE" --var "band_id=position()-1" \
    --if '//RADIO_ADD_OFFSET[@band_id=$band_id]' \
    -v "." -o "," -v "//RADIO_ADD_OFFSET[@band_id=\$band_id]" -nl l1c-metadata.xml); do

    fname=${op%,*}
    fname=${fname:(-3)}  # extract B?? from long file name
    offset=${op#*,}

    echo "Applying Pixel Data Offset ${offset} to ${fname}.jp2"

    echo Running gdal_calc.py -A "${fname}.jp2" --outfile=temp.tif --calc="numpy.where(A == 0, 0, A+${offset})"
    gdal_calc.py -A "${fname}.jp2" --outfile=temp.tif --calc="numpy.where(A == 0, 0, A+${offset})"
    echo Running gdal_translate -a_nodata none -co QUALITY=100 -co REVERSIBLE=YES -co YCBCR420=NO temp.tif "${fname}.jp2"
    gdal_translate -a_nodata none --config GDAL_PAM_ENABLED NO -co QUALITY=100 -co REVERSIBLE=YES -co YCBCR420=NO temp.tif "${fname}.jp2"
    rm -f temp.tif
done

# Use xmlstarlet again to delete the Radiometric Offset section
cp l1c-metadata.xml l1c-metadata.xml.orig
xmlstarlet ed --pf -d "//Radiometric_Offset_List" l1c-metadata.xml.orig > l1c-metadata.xml
