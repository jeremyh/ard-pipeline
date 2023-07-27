FROM ubuntu:20.04
RUN apt-get update -y \
 && DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --fix-missing --no-install-recommends awscli \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
COPY ./modtran_runner ./modtran_runner
CMD [ "/opt/modtran_runner/modtran_runner.sh" ]
