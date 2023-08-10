
@default: run

# editable and no-build-islation together will allow meson to auto-compile
# the native dependencies when running from your source directory.
#
# (Not-doing-this is probably why you're getting import errors running tests!)
#
@install-dev:
    python3 -m pip install --no-build-isolation --editable .

@build:
    docker build --platform linux/amd64 -t ard:dev .

@build-native:
    docker build -t ard:native .

@run:
    docker run -it --rm --volume "${PWD}:/tests" --user root -w /tests ard:dev /bin/bash

# Run tests in Docker
@test:
    docker run --rm --volume "${PWD}":/tests -w /tests ard:dev pytest
