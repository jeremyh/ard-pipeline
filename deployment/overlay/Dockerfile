FROM 538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dev/wagl:rc-20190109-5
USER root
RUN mkdir /upload
RUN chown -R wagl_nrt:wagl_nrt /upload

RUN apt-get update && apt-get -y install --no-install-recommends xmlstarlet && rm -rf /var/lib/apt/lists/*

USER wagl_nrt
COPY scripts/remove_l1_dn_offsets.sh /scripts/remove_l1_dn_offsets.sh
COPY scripts/process-scene.sh /scripts/process-scene.sh
COPY scripts/luigi.cfg /scripts/luigi.cfg
COPY scripts/check_exists.py /scripts/check_exists.py
ENTRYPOINT []
CMD []
