FROM ubuntu:focal as builder
SHELL ["/bin/bash", "-c"]

ENV BUILD_DIR=/build
ENV PATH="${PATH}:${BUILD_DIR}/conda/bin"
ENV IDLFUNCTIONS_VERSION=0.5.4
ENV PYTHON_FMASK_VERSION=0.5.7
ENV EODATASETS3_VERSION=eodatasets3-0.29.0
ENV PYTHONPATH=${BUILD_DIR}/conda/lib/python3.8/site-packages/
ARG BUILDPLATFORM
ARG TARGETARCH

USER root

# Build deps
RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --fix-missing --no-install-recommends \
        git bzip2 ca-certificates gfortran-10 gcc-10 make software-properties-common libpq-dev wget \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s $(which gfortran-10) $(which gfortran-10 | sed 's/\(.*\)\/\gfortran-10/\1\/gfortran/') \
    && ln -s $(which gcc-10) $(which gcc-10 | sed 's/\(.*\)\/\gcc-10/\1\/gcc/')

WORKDIR ${BUILD_DIR}

RUN echo I am running on $BUILDPLATFORM, building for $TARGETARCH

# Bump this when newer versions of python are required
RUN if [[ "$TARGETARCH" == "arm64" ]] ; then export archname="aarch64"; else export archname="x86_64" ; fi; \
    wget -O /root/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-py38_23.5.2-0-Linux-${archname}.sh \
    && chmod +x /root/miniconda.sh && /root/miniconda.sh -b -f -p conda && rm /root/miniconda.sh

RUN pip install awscli boto boto3

RUN conda install mamba -n base -c conda-forge

# GDAL 3.1 is being used because https://gdal.org/api/python.html#usage
RUN mamba install -y -c conda-forge \
        bitshuffle==0.3.5 \
        blosc==1.21.0 \
        blosc-hdf5-plugin==1.0.0 \
        boost-cpp==1.74.0 \
        cairo==1.16.0 \
        certifi==2021.5.30 \
        click==7.1.2 \
        cython==0.29.24 \
        gdal==3.1.4 \
        h5py==3.3.0 \
        hdf5plugin==2.3.2 \
        hdf5-external-filter-plugins-bitshuffle==0.1.0 \
        libnetcdf==4.7.4 \
        numpy==1.23.0 \
        proj==7.1.1 \
        python-fmask==0.5.7 \
        scipy==1.8.1 \
        rasterio==1.2.1 \
    && conda clean --all -y

# Download the necessary codebases (@versions) (using git now as installs needed version info)
RUN pip install "git+https://github.com/sixy6e/idl-functions.git@${IDLFUNCTIONS_VERSION}#egg=idl-functions" \
    "git+https://github.com/GeoscienceAustralia/eo-datasets.git@${EODATASETS3_VERSION}#egg=eodatasets3" \
    "git+https://github.com/ubarsc/rios@rios-1.4.10#egg=rios-1.4.10" \
    "git+https://github.com/ubarsc/python-fmask@pythonfmask-0.5.7#egg=python-fmask-${PYTHON_FMASK_VERSION}"

WORKDIR /code
ADD . ./
RUN pip install .

FROM ubuntu:focal as prod

# locale variables required by Click
ENV LC_ALL="C.UTF-8"
ENV LANG="C.UTF-8"

ENV BUILD_DIR=/build
ENV PATH="${PATH}:${BUILD_DIR}/conda/bin"
ENV PYTHONPATH=${BUILD_DIR}/conda/lib/python3.8/site-packages/

RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libgfortran5 \
        jq \
        awscli \
        xmlstarlet \
        libjpeg62 \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# install libpng12
# COPY deployment/lib /build-lib
# RUN dpkg -i /build-lib/libpng12-0_1.2.54-1ubuntu1.1+1~ppa0~focal_amd64.deb \
      # && rm -rf /build-lib

RUN mkdir /scripts /granules /output /upload

COPY --from=builder ${BUILD_DIR} ${BUILD_DIR}
COPY deployment/scripts /scripts
COPY deployment/configs /configs
