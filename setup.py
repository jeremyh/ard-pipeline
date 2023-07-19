#!/usr/bin/env python

import setuptools
from numpy.distutils.core import setup


def configuration(parent_package="", top_path=None):
    from numpy.distutils.misc_util import Configuration

    config = Configuration(None, parent_package, top_path)
    config.set_options(
        ignore_setup_xxx_py=True,
        assume_default_configuration=True,
        delegate_options_to_subpackages=True,
    )

    config.add_subpackage("wagl")
    # config.add_subpackage("tesp")
    # config.add_subpackage("eugl")
    return config


setup(
    name="ard-pipeline",
    configuration=configuration,
    use_scm_version=True,
    setup_requires=["pytest-runner", "setuptools_scm", "numpy"],
    url="https://github.com/GeoscienceAustralia/wagl",
    license="CC0 1.0 Universal",
    author="Geoscience Australia",
    author_email="earth.observation@ga.gov.au",
    maintainer="Geoscience Australia",
    packages=setuptools.find_packages(include=("wagl", "eugl", "tesp")),
    scripts=[
        "utils/test_satellite_solar_angles",
        "utils/test_dsm",
        "utils/test_exiting_angles",
        "utils/test_incident_angles",
        "utils/test_relative_slope",
        "utils/test_terrain_shadow_masks",
        "utils/test_slope_aspect",
        "utils/aot_converter",
        "utils/wagl_convert",
        "utils/wagl_ls",
        "utils/wagl_residuals",
        "utils/wagl_pbs",
        "bin/s2package",
        "bin/ard_pbs",
        "bin/search_s2",
        "bin/batch_summary",
    ],
    tests_require=[
        "pytest",
        "deepdiff",
    ],
    install_requires=[
        "attrs>=17.4.0",
        "checksumdir",
        "ciso8601",
        "click",
        "click_datetime",
        "eodatasets3>=0.19.2",
        "ephem>=3.7.5.3",
        "fiona>=1.7.0",
        "folium",
        "GDAL>=1.9.2",
        "geopandas>=0.1.1",
        "h5py>=2.5.0",
        "idl-functions>=0.5.2",  # custom package via git, not pypi
        "importlib-metadata;python_version<'3.8'",
        "luigi>2.7.6",
        "nested_lookup>=0.1.3",
        "numexpr>=2.4.6",
        "numpy>=1.8",
        "pandas>=0.17.1",
        "pyproj>1.9.5",
        "python-dateutil>=2.6.1",
        "python-fmask==0.5.7",
        "pyyaml>=3.11",
        "rasterio>1,!=1.0.3.post1,!=1.0.3",  # issue with /vsizip/ reader
        "rios",
        "s2cloudless==1.5.0",
        "scikit-image>=0.8.2",
        "scipy>=0.14",
        "sentinelhub==3.4.2",
        "shapely>=1.5.13",
        "structlog>=16.1.0",
        "tables>=3.4.2",
    ],
    # Was needed for tesp .. here too? TODO
    include_package_data=True,
    package_data={"eugl.gqa": ["data/*.csv"]},
    dependency_links=[
        "git+git://github.com/sixy6e/idl-functions.git@master#egg=idl-functions-0.5.2",
        "git+https://github.com/ubarsc/rios@rios-1.4.10#egg=rios-1.4.10",
        "git+https://github.com/ubarsc/python-fmask@pythonfmask-0.5.7#egg=python-fmask-0.5.7",  # noqa: E501
    ],
)
