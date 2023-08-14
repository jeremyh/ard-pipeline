#!/usr/bin/env bash

set -eux

clean_all=false

if [ "$clean_all" = true ]; then
     pip_args=(--no-cache-dir --force-reinstall)
fi

location="conda"
# If they provided a location argument, install there instead
if [ $# -gt 0 ]; then
    location="$1"
fi

mkdir -p "${location}"

# TODO: Or in Docker, should it be "$TARGETARCH"?
arch="$(uname -m)"
if [ "$arch" = "aarch64" ]; then
  archname="aarch64"
else
  archname="x86_64"
fi

conda_inst="${location}/miniconda.sh"

wget --progress=dot:giga \
    -O "${conda_inst}" \
    "https://repo.anaconda.com/miniconda/Miniconda3-py311_23.5.2-0-Linux-${archname}.sh"

chmod +x "${conda_inst}"

"${conda_inst}" -b -f -p "${location}"
rm "${conda_inst}"

conda install mamba -n base -c conda-forge

mamba install -y -c conda-forge \
            blosc \
            boost-cpp \
            cairo \
            certifi \
            click \
            cython \
            gdal \
            h5py \
            hdf5-external-filter-plugins-bitshuffle \
            hdf5plugin \
            libnetcdf \
            lightgbm \
            numpy \
            proj \
            pytables \
            python-fmask \
            rasterio \
            scikit-image \
            scipy

pip install "${pip_args[@]}" \
    "git+https://github.com/sixy6e/idl-functions.git@0.5.4#egg=idl-functions" \
    "git+https://github.com/ubarsc/rios@rios-1.4.10#egg=rios" \
    "git+https://github.com/ubarsc/python-fmask@pythonfmask-0.5.7#egg=python-fmask" \
    awscli boto boto3

if [ "$clean_all" = true ]; then
    conda clean --all -y
fi
