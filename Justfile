
@default: run

# editable and no-build-islation together will allow meson to auto-compile
# the native dependencies when running from your source directory.
#
# (Not-doing-this is probably why you're getting import errors running tests!)
#
@install-dev:
    python3 -m pip install --no-build-isolation --editable .

@build-conda:
    docker build --platform linux/amd64 -t ard:conda -f Dockerfile.conda-native .

@build:
    docker build --platform linux/amd64 -t ard:dev .

@build-native:
    docker build -t ard:native .

@run:
    docker run --platform linux/amd64 -it --rm --volume "${PWD}:/tests" -w /tests ard:dev /bin/bash -l
@root:
    docker run --platform linux/amd64 -it --rm --volume "${PWD}:/tests" --user root -w /tests ard:dev /bin/bash -l

@py:
    docker run -it --rm --volume "${PWD}:/tests" -w /tests ard:dev python

@take-env:
    docker run --rm --volume "${PWD}:/tests" --user root -w /tests ard:dev 'pip uninstall ard-pipeline rios python-fmask idl-functions -y; conda env export > /tests/deployment/environment.yaml'


# Run tests in Docker
@test:
    docker run --rm --volume "${PWD}/tests":/tests -w /tests ard:dev pytest
