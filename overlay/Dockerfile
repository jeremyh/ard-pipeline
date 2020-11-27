FROM 451924316694.dkr.ecr.ap-southeast-2.amazonaws.com/dev/wagl:rc-20190109-5
USER root
RUN mkdir /upload
RUN chown -R wagl_nrt:wagl_nrt /upload
USER wagl_nrt
COPY scripts/process-scene.sh /scripts/process-scene.sh
COPY scripts/luigi.cfg /scripts/luigi.cfg
ENTRYPOINT []
CMD []
