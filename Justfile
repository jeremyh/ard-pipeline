
@default: run

@build:
    docker build --platform linux/amd64 -t ard:dev .

@build-native:
    docker build -t ard:native .


@run:
    docker run -it --rm --volume "${PWD}:/tests" --user root -w /tests ard:dev /bin/bash
