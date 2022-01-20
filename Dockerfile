FROM ubuntu:focal as builder
SHELL ["/bin/bash", "-c"]

ENV BUILD_DIR=/build
ENV PATH="${PATH}:${BUILD_DIR}/conda/bin"
ENV WAGL_VERSION=wagl-5.6.0
ENV EUGL_VERSION=eugl-0.4.0
ENV TESP_VERSION=tesp-0.9.0
ENV EODATASETS1_VERSION=eodatasets-0.12
ENV EODATASETS3_VERSION=eodatasets3-0.22.2
ENV PYTHONPATH=${BUILD_DIR}/conda/lib/python3.8/site-packages/

USER root

# Build deps
RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --fix-missing --no-install-recommends \
        git bzip2 ca-certificates gfortran-10 gcc-10 make software-properties-common libpq-dev wget \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s $(which gfortran-10) $(which gfortran-10 | sed 's/\(.*\)\/\gfortran-10/\1\/gfortran/') \
    && ln -s $(which gcc-10) $(which gcc-10 | sed 's/\(.*\)\/\gcc-10/\1\/gcc/')

WORKDIR ${BUILD_DIR}

# Bump this when newer versions of python are required
RUN wget -O /root/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-py38_4.8.2-Linux-x86_64.sh \
    && chmod +x /root/miniconda.sh && /root/miniconda.sh -b -f -p conda && rm /root/miniconda.sh

RUN pip install awscli boto boto3

# GDAL 3.1 is being used because https://gdal.org/api/python.html#usage
RUN conda install -y -c conda-forge \
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
        matplotlib==3.4.3 \
        numpy==1.22.0 \
        proj==7.1.1 \
        python==3.8.2 \
        python-fmask==0.5.5 \
        scipy==1.7.0 \
    && conda clean --all -y

# Download the necessary codebases (@versions) (using git now as installs needed version info)
RUN git clone --branch master https://github.com/sixy6e/idl-functions.git idl-functions \
    && cd ${BUILD_DIR}/idl-functions && pip install . && rm -rf .git

RUN git clone --branch ${EODATASETS1_VERSION} https://github.com/GeoscienceAustralia/eo-datasets.git eodatasets1 \
    && cd ${BUILD_DIR}/eodatasets1 && pip install . && rm -rf .git

RUN git clone --branch ${EODATASETS3_VERSION} https://github.com/GeoscienceAustralia/eo-datasets.git eodatasets3 \
    && cd ${BUILD_DIR}/eodatasets3 && pip install . && rm -rf .git

RUN git clone --branch ${WAGL_VERSION} https://github.com/GeoscienceAustralia/wagl.git wagl \
    && cd ${BUILD_DIR}/wagl && pip install . && rm -rf .git

RUN git clone --branch ${EUGL_VERSION} https://github.com/OpenDataCubePipelines/eugl.git eugl \
    && cd ${BUILD_DIR}/eugl && pip install . && rm -rf .git

RUN git clone --branch ${TESP_VERSION} https://github.com/OpenDataCubePipelines/tesp.git tesp \
    && cd ${BUILD_DIR}/tesp && pip install . && rm -rf .git

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
        libjpeg62 \
    && rm -rf /var/lib/apt/lists/*

# install libpng12
COPY lib /build-lib
RUN dpkg -i /build-lib/libpng12-0_1.2.54-1ubuntu1.1+1~ppa0~focal_amd64.deb && rm -rf /build-lib

RUN mkdir /scripts /granules /output /upload

COPY --from=builder ${BUILD_DIR} ${BUILD_DIR}
COPY scripts /scripts
COPY configs /configs
