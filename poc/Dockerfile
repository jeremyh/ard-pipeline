FROM ubuntu:focal as builder
SHELL ["/bin/bash", "-c"]

ENV BUILD_DIR=/build
ENV PATH="${PATH}:${BUILD_DIR}/conda/bin:${BUILD_DIR}/bin"
ENV WAGL_VERSION=develop
ENV EUGL_VERSION=master
ENV TESP_VERSION=master
ENV PYTHONPATH=${BUILD_DIR}/lib/python3.8/site-packages/

USER root

# Build deps
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git bzip2 ca-certificates gfortran-10 gcc-10 make software-properties-common libpq-dev

RUN ln -s $(which gfortran-10) $(which gfortran-10 | sed 's/\(.*\)\/\gfortran-10/\1\/gfortran/') \
    && ln -s $(which gcc-10) $(which gcc-10 | sed 's/\(.*\)\/\gcc-10/\1\/gcc/')

WORKDIR ${BUILD_DIR}

# Bump this when newer versions of python are required
ADD https://repo.continuum.io/miniconda/Miniconda3-py38_4.8.2-Linux-x86_64.sh /root/miniconda.sh
RUN chmod +x /root/miniconda.sh && /root/miniconda.sh -b -f -p conda

# Force versions
RUN pip install numpy \
    && conda install \
        # hdf5==1.12.0 \
        blosc==1.21.0 \
        click==7.1.2 -y

RUN conda install -c conda-forge \
        gdal==3.3.0 \
        python-fmask==0.5.5
        # hdf5plugin==2.3.2

# Download the necessary codebases (@versions) (using git now as installs needed version info)
RUN git clone --branch master https://github.com/sixy6e/idl-functions.git idl-functions \
    && git clone --branch eodatasets1 https://github.com/GeoscienceAustralia/eo-datasets.git eodatasets1 \
    && git clone --branch eodatasets3-0.19.3 https://github.com/GeoscienceAustralia/eo-datasets.git eodatasets3 \
    && git clone --branch ${TESP_VERSION} https://github.com/OpenDataCubePipelines/tesp.git tesp \
    && git clone --branch ${EUGL_VERSION} https://github.com/OpenDataCubePipelines/eugl.git eugl \
    && git clone --branch ${WAGL_VERSION} https://github.com/GeoscienceAustralia/wagl.git wagl

RUN cd ${BUILD_DIR}/idl-functions && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/wagl && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/eodatasets1 && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/eodatasets3 && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/eugl && pip install . && rm -rf .git \
    && cd ${BUILD_DIR}/tesp && pip install . && rm -rf .git

RUN conda clean --all -y

FROM ubuntu:focal as prod

ENV BUILD_DIR=/build
ENV PATH="${PATH}:${BUILD_DIR}/conda/bin:${BUILD_DIR}/bin"
ENV PYTHONPATH=${BUILD_DIR}/lib/python3.8/site-packages/

RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libgfortran5 \
        jq \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder ${BUILD_DIR} ${BUILD_DIR}
