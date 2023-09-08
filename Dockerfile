# syntax = docker/dockerfile:1.5
FROM ubuntu:focal as builder
SHELL ["/bin/bash", "-c"]

ENV BUILD_DIR=/build
ARG BUILDPLATFORM
ARG TARGETARCH

USER root

# Build deps
RUN apt-get update -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --fix-missing --no-install-recommends \
       git bzip2 libtiff5 ca-certificates gfortran-10 gcc-10 make software-properties-common libpq-dev wget libarchive13 \
    && rm -rf /var/lib/apt/lists/*

RUN set -o pipefail; \
    ln -s "$(which gfortran-10)" "$(which gfortran-10 | sed 's/\(.*\)\/\gfortran-10/\1\/gfortran/')" \
 && ln -s "$(which gcc-10)" "$(which gcc-10 | sed 's/\(.*\)\/\gcc-10/\1\/gcc/')"

WORKDIR ${BUILD_DIR}

# Bump this when newer versions of python are required
COPY deployment/create-conda-environment.sh deployment/environment.yaml /root/
RUN /root/create-conda-environment.sh
# Use conda for the remaining commands
SHELL ["/build/conda/bin/conda", "run", "--no-capture-output", "-n", "ard", "/bin/bash", "-c"]

WORKDIR /code
COPY docs ./docs
COPY utils ./utils
COPY eugl ./eugl
COPY tesp ./tesp
COPY wagl ./wagl
COPY pyproject.toml meson.build LICENCE.md README.md ./
# hadolint shell=/bin/bash
RUN pip install --no-cache-dir .
# hadolint shell=/bin/bash
RUN adduser --disabled-password --gecos '' user
USER user

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
	libtiff5 \
        xmlstarlet \
        libjpeg62 \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# install libpng12
# COPY deployment/lib /build-lib
# RUN dpkg -i /build-lib/libpng12-0_1.2.54-1ubuntu1.1+1~ppa0~jammy_amd64.deb \
      # && rm -rf /build-lib

RUN mkdir /scripts /granules /output /upload

COPY --from=builder ${BUILD_DIR} ${BUILD_DIR}
COPY deployment/scripts /scripts
COPY deployment/configs /configs
RUN /build/conda/bin/conda init bash

ENV PYTHONFAULTHANDLER=1

RUN adduser --disabled-password --gecos '' user
USER user
RUN /build/conda/bin/conda init bash
RUN echo "conda activate ard" >> ~/.bashrc
