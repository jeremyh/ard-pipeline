FROM ubuntu:20.04
RUN apt update -y
RUN apt install -y --fix-missing --no-install-recommends awscli
COPY ./modtran_runner ./modtran_runner
CMD [ "/modtran_runner/modtran_runner.sh" ]
