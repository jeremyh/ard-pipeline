"""Setup gaip."""


from numpy.distutils.core import setup

import versioneer


def configuration(parent_package="", top_path=None):
    from numpy.distutils.misc_util import Configuration

    config = Configuration(None, parent_package, top_path)
    config.set_options(
        ignore_setup_xxx_py=True,
        assume_default_configuration=True,
        delegate_options_to_subpackages=True,
    )

    config.add_subpackage("gaip")
    return config


setup(
    name="gaip",
    configuration=configuration,
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    url="https://github.com/GeoscienceAustralia/gaip",
    license="CC0 1.0 Universal",
    author="The gaip authors",
    maintainer="gaip developers",
    scripts=[
        "utils/test_satellite_solar_angles",
        "utils/test_dsm",
        "utils/test_exiting_angles",
        "utils/test_incident_angles",
        "utils/test_relative_slope",
        "utils/test_terrain_shadow_masks",
        "utils/test_slope_aspect",
        "utils/aot_converter",
        "utils/gaip_convert",
        "utils/gaip_ls",
        "utils/gaip_residuals",
        "utils/gaip_pbs",
    ],
)
