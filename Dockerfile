# syntax = docker/dockerfile:1.5

FROM ubuntu:focal as builder
SHELL ["/bin/bash", "-c"]

ENV BUILD_DIR=/build
ARG BUILDPLATFORM
ARG TARGETARCH

USER root

# Build deps
RUN --mount=type=cache,target=/var/cache/apt,id=aptbuild <<EOF
    set -eu
    apt-get update -y;
    DEBIAN_FRONTEND=noninteractive apt-get install -y --fix-missing --no-install-recommends \
        bzip2 \
        ca-certificates \
        gcc-10 \
        gfortran-10 \
        git \
        libarchive13 \
        libpq-dev \
        libtiff5 \
        make \
        software-properties-common \
        wget
    rm -rf /var/lib/apt/lists/*
EOF

RUN set -o pipefail; \
    ln -s "$(which gfortran-10)" "$(which gfortran-10 | sed 's/\(.*\)\/\gfortran-10/\1\/gfortran/')" \
 && ln -s "$(which gcc-10)" "$(which gcc-10 | sed 's/\(.*\)\/\gcc-10/\1\/gcc/')"

WORKDIR /build

# Override the default in the conda-environment creator
ARG fmask_version=0.5.7

COPY deployment/create-conda-environment.sh deployment/environment.yaml ./
RUN --mount=type=cache,target=/opt/conda/pkgs,id=conda \
    --mount=type=cache,target=/root/.cache,id=pip \
    ./create-conda-environment.sh /opt/conda

# Use conda for the remaining commands
SHELL ["/opt/conda/bin/conda", "run", "--no-capture-output", "-n", "ard", "/bin/sh", "-c"]

# We copy just the relevant things to maximise caching.
WORKDIR /code
COPY docs ./docs
COPY utils ./utils
COPY eugl ./eugl
COPY tesp ./tesp
COPY wagl ./wagl
# Needed to read version number
COPY .git ./.git
COPY pyproject.toml meson.build LICENCE.md README.md ./

RUN pip install .

FROM ubuntu:focal as prod

# locale variables required by Click
ENV LC_ALL="C.UTF-8"
ENV LANG="C.UTF-8"

RUN --mount=type=cache,target=/var/cache/apt,id=aptprod <<EOF
    set -eu
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libgfortran5 \
        jq \
        awscli \
        libarchive13 \
        libtiff5 \
        xmlstarlet \
        libjpeg62 \
        unzip
    rm -rf /var/lib/apt/lists/*
EOF

RUN mkdir /scripts /granules /output /upload

COPY --from=builder /opt/conda /opt/conda
COPY deployment/scripts /scripts
COPY deployment/configs /configs
COPY deployment/check-environment.sh /scripts
RUN /opt/conda/bin/conda init bash

ENV PYTHONFAULTHANDLER=1

RUN adduser --disabled-password --gecos '' user
USER user
RUN /opt/conda/bin/conda init bash
RUN echo "conda activate ard" >> ~/.bashrc
ENTRYPOINT ["/opt/conda/bin/conda", "run", "--no-capture-output", "-n", "ard", "/bin/bash", "-c"]
