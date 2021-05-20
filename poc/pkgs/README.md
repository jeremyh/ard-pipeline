## CMDS
```
docker build --rm -t python-poc -f Dockerfile.pip .
```
```
docker run --rm -it \
    -v $(pwd)/pkgs/hello-world:/app/hello-world \
    -v $(pwd)/pkgs/hello-satan:/app/hello-satan \
    python-poc \
    bash
```