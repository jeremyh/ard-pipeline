# ARD Pipeline
------

A Python package for producing standarised imagery in the form of:

* Nadir Bi-directional Reflectance Distribution Function Adjusted Reflectance (NBAR)
* NBART; NBAR with Terrain Illumination correction
* Surface Brightness Temperature
* Pixel Quality (per pixel metadata)

The luigi task workflow for producing NBAR for a Landsat 5TM scene is given below.

![](docs/source/diagrams/luigi-task-visualiser-reduced.png)

## Supported Satellites and Sensors
-----------------------------------
* Landsat 5 TM
* Landsat 7 ETM
* Landsat 8 OLI
* Landsat 8 TIRS
* Sentinel-2a

## Development
---------------

A [Justfile](https://github.com/casey/just) is included in the repo for running common commands.

### Dependencies

You can either create your own environment, or use the provided [Dockerfile](Dockerfile).

If building your own environment, miniconda is recommended dur to the large number of
native dependencies.

A script is provided to build conda with needed dependencies:

```
    # Create environment in ~/conda directory
    ./deployment/create-conda-environment.sh ~/conda

    # Activate the environment in the current shell
    ~/conda/bin/activate

    # Build ARD for development
    pip install --no-build-isolation --editable .
```

### Import errors

If you try running code directly from the source repository, such
as in running tests, you may see import errors such as this:
`from wagl.__sat_sol_angles import angle`

These are due to the native modules (c, fortran) needing built
in the repo.

You can avoid this, and still maintain live editing, by
doing a non-isolated editable install:

```
    python3 -m pip install --no-build-isolation --editable .
```

Meson will then auto-build the native modules as needed and
you can run directly from your source directory.

Run checks locally using the `./check-code.sh` file.

### Additional HDF5 compression filters (optional)
Additional compression filters can be used via HDF5's
[dynamically loaded filters](https://support.hdfgroup.org/HDF5/doc/Advanced/DynamicallyLoadedFilters/HDF5DynamicallyLoadedFilters.pdf).
Essentially the filter needs to be compiled against the HDF5 library, and
installed into HDF5's plugin path, or a path of your choosing, and set the
HDF5_PLUGIN_PATH environment variable. The filters are then automatically
accessible by HDF5 via the [integer code](https://support.hdfgroup.org/services/contributions.html)
assigned to the filter.

#### Mafisc compression filter
Mafisc combines both a bitshuffling filter and lzma compression filter in order
to get the best compression possible at the cost of lower compression speeds.
To install the `mafisc` compression filter, follow these [instructions](https://wr.informatik.uni-hamburg.de/research/projects/icomex/mafisc).

#### Bitshuffle
The [bitshuffle filter](https://github.com/kiyo-masui/bitshuffle) can be installed
from source, or conda via the supplied [conda recipe](https://github.com/kiyo-masui/bitshuffle/tree/master/conda-recipe).
It utilises a bitshuffling filter on top of either a lz4 or lzf compression filter.

## Basic command line useage
--------------------------
Using the [local scheduler](http://luigi.readthedocs.io/en/stable/command_line.html):

    $ luigi --module wagl.multifile_workflow ARD --workflow NBAR --level1-list scenes.txt --outdir /some/path --local-scheduler --workers 4

Using the [central scheduler](http://luigi.readthedocs.io/en/stable/central_scheduler.html):

    $ luigid --background --pidfile <PATH_TO_PIDFILE> --logdir <PATH_TO_LOGDIR> --state-path <PATH_TO_STATEFILE>

    $ luigi --module wagl.multifile_workflow ARD --level1-list scenes.txt --workflow STANDARD --outdir /some/path --workers 4

    $ luigi --module wagl.multifile_workflow ARD --level1-list scenes.txt --workflow NBAR --outdir /some/path --workers 4

    $ luigi --module wagl.multifile_workflow ARD --level1-list scenes.txt --workflow SBT --outdir /some/path --workers 4
