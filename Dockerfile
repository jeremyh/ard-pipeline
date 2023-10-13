# syntax = docker/dockerfile:1.5
# We use rockylinux 8.8 to match the NCI gadi environment.
FROM rockylinux:8.8 as builder
SHELL ["/bin/bash", "-c"]

ENV BUILD_DIR=/build \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL="C.UTF-8" \
    LANG="C.UTF-8" \
    PYTHONFAULTHANDLER=1

ARG BUILDPLATFORM
ARG TARGETARCH

USER root

# Build deps
RUN --mount=type=cache,target=/var/cache/dnf,id=dnfbuild <<EOF
    set -eu
    dnf --quiet makecache --refresh
    dnf --assumeyes --quiet install \
        bzip2 \
        ca-certificates \
        libarchive \
        libtiff-devel \
        findutils \
        gcc \
        gcc-gfortran \
        git \
        make \
        wget
EOF

WORKDIR /build

# Override the default in the conda-environment creator
ARG fmask_version=0.5.7

COPY deployment/create-conda-environment.sh deployment/environment.yaml ./
RUN --mount=type=cache,target=/opt/conda/pkgs,id=conda \
    --mount=type=cache,target=/root/.cache,id=pip \
    ./create-conda-environment.sh /opt/conda

# Use conda for the remaining commands
SHELL ["/opt/conda/bin/conda", "run", "--no-capture-output", "/bin/sh", "-c"]


RUN --mount=type=bind,target=/code,readonly,source=. \
    --mount=type=cache,target=/root/.cache,id=pip \
    --mount=type=tmpfs,target=/tmp <<EOF
    set -eu
    cd /code
    pip install -v --config-settings=builddir=/tmp/ard-pipeline-build .
EOF


FROM rockylinux:8.8 as prod

# locale variables required by Click
ENV LC_ALL="C.UTF-8" \
    LANG="C.UTF-8" \
    PYTHONFAULTHANDLER=1

RUN --mount=type=cache,target=/var/cache/dnf,id=dnfprod <<EOF
    set -eu
    dnf --quiet makecache --refresh
    dnf --assumeyes --quiet install \
        libgfortran \
        libarchive \
        libtiff \
        findutils \
        jq \
        xmlstarlet \
        unzip \
        which
EOF

RUN mkdir /scripts /granules /output /upload

COPY --from=builder /opt/conda /opt/conda
COPY deployment/scripts /scripts
COPY deployment/configs /configs
COPY deployment/check-environment.sh /scripts
RUN /opt/conda/bin/conda init bash

RUN useradd -m user
USER user
RUN /opt/conda/bin/conda init bash
ENTRYPOINT ["/opt/conda/bin/conda", "run", "--no-capture-output", "/bin/bash", "-c"]
