FROM ubuntu:focal as builder
SHELL ["/bin/bash", "-c"]

ENV BUILD_DIR=/build
ENV PATH="${PATH}:${BUILD_DIR}/conda/bin"
ENV WAGL_VERSION=develop
ENV EUGL_VERSION=master
ENV TESP_VERSION=master
ENV EODATASETS1_VERSION=eodatasets-0.12
ENV EODATASETS3_VERSION=eodatasets3-0.20.1
ENV PYTHONPATH=${BUILD_DIR}/conda/lib/python3.8/site-packages/

USER root

# Build deps
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --fix-missing --no-install-recommends \
        git bzip2 ca-certificates gfortran-10 gcc-10 make software-properties-common libpq-dev

RUN ln -s $(which gfortran-10) $(which gfortran-10 | sed 's/\(.*\)\/\gfortran-10/\1\/gfortran/') \
    && ln -s $(which gcc-10) $(which gcc-10 | sed 's/\(.*\)\/\gcc-10/\1\/gcc/')

WORKDIR ${BUILD_DIR}

# Bump this when newer versions of python are required
ADD https://repo.continuum.io/miniconda/Miniconda3-py38_4.8.2-Linux-x86_64.sh /root/miniconda.sh
RUN chmod +x /root/miniconda.sh && /root/miniconda.sh -b -f -p conda

# Force versions
RUN pip install awscli boto boto3 numpy \
    && conda install \
        blosc==1.21.0 \
        click==7.1.2 -y

# GDAL 3.1 is being used because https://gdal.org/api/python.html#usage
RUN conda install -c conda-forge \
        gdal==3.1.4 \
        python-fmask==0.5.5

# Download the necessary codebases (@versions) (using git now as installs needed version info)
RUN git clone --branch master https://github.com/sixy6e/idl-functions.git idl-functions \
    && git clone --branch ${EODATASETS1_VERSION} https://github.com/GeoscienceAustralia/eo-datasets.git eodatasets1 \
    && git clone --branch ${EODATASETS1_VERSION} https://github.com/GeoscienceAustralia/eo-datasets.git eodatasets3 \
    && git clone --branch ${TESP_VERSION} https://github.com/OpenDataCubePipelines/tesp.git tesp \
    && git clone --branch ${EUGL_VERSION} https://github.com/OpenDataCubePipelines/eugl.git eugl \
    && git clone --branch ${WAGL_VERSION} https://github.com/GeoscienceAustralia/wagl.git wagl

RUN cd ${BUILD_DIR}/idl-functions && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/wagl && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/eodatasets1 && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/eodatasets3 && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/eugl && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/tesp && pip install . && rm -rf .git

RUN conda install -c conda-forge hdf5plugin==2.3.2 \
        blosc-hdf5-plugin==1.0.0 \
        bitshuffle==0.3.5 \
        hdf5-external-filter-plugins-bitshuffle==0.1.0

RUN conda clean --all -y

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
    && rm -rf /var/lib/apt/lists/*

RUN mkdir /scripts /granules /output /upload

COPY --from=builder ${BUILD_DIR} ${BUILD_DIR}
COPY scripts/process-scene-sentinel-2.sh /scripts/process-scene-sentinel-2.sh
COPY scripts/s2-l1c-aws-pds-generate-metadata.py /scripts/s2-l1c-aws-pds-generate-metadata.py
COPY scripts/luigi-sentinel-2.cfg /scripts/luigi-sentinel-2.cfg
COPY scripts/luigi-landsat.cfg /scripts/luigi-landsat.cfg
COPY scripts/luigi-logging.cfg /scripts/luigi-logging.cfg
COPY scripts/check-exists.py /scripts/check-exists.py
RUN chmod +x /scripts/process-scene-sentinel-2.sh
