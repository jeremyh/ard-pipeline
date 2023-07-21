"""Setup
-----.

This compiles all the Fortran extensions.
"""


def configuration(parent_package="", top_path=None):
    # pylint: disable=expression-not-assigned

    from numpy.distutils.misc_util import Configuration



    _cast_shadow_mask = py3.extension_module("_cast_shadow_mask",
        [
            "f90_sources/sys_variables.f90",
            "f90_sources/cast_shadow_main.f90",
            "f90_sources/terrain_border_margins.f90",
            "f90_sources/cast_shadow_mask.f90",
            "f90_sources/terrain_occlusion.f90",
            "f90_sources/geo2metres_pixel_size.f90",
        ],
        install: true,
        link_language: 'fortran',
        subdir: 'wagl'
    ),
    _exiting_angle = py3.extension_module("_exiting_angle",
        [
            "f90_sources/sys_variables.f90",
            "f90_sources/exiting_angle.f90",
            "f90_sources/earth_rotation.f90",
        ],
                                          install: true,
    link_language: 'fortran',
    subdir: 'wagl'
    ),
    _incident_angle = py3.extension_module("_incident_angle",
        [
            "f90_sources/incident_angle.f90",
            "f90_sources/earth_rotation.f90",
        ],
                                           install: true,
    link_language: 'fortran',
    subdir: 'wagl'
    ),
    _slope_aspect = py3.extension_module("_slope_aspect",
        [
            "f90_sources/sys_variables.f90",
            "f90_sources/slope_aspect.f90",
            "f90_sources/geo2metres_pixel_size.f90",
        ],
                                         install: true,
    link_language: 'fortran',
    subdir: 'wagl'
    ),
    _surface_reflectance = py3.extension_module("_surface_reflectance",
        [
            "f90_sources/surface_reflectance.f90",
            "f90_sources/white_sky.f90",
            "f90_sources/black_sky.f90",
            "f90_sources/brdf_shape.f90",
        ],
                                                install: true,
    link_language: 'fortran',
    subdir: 'wagl'
    ),
    _satellite_model = py3.extension_module("_satellite_model",
        [
            "f90_sources/sys_variables.f90",
            "f90_sources/geo2metres_pixel_size.f90",
            "f90_sources/satellite_model.f90",
        ],
                                            install: true,
    link_language: 'fortran',
    subdir: 'wagl'
    ),
    _track_time_info = py3.extension_module("_track_time_info",
        [
            "f90_sources/sys_variables.f90",
            "f90_sources/geod2geo.f90",
            "f90_sources/q_cal.f90",
            "f90_sources/geo2metres_pixel_size.f90",
            "f90_sources/satellite_track.f90",
            "f90_sources/track_time_info.f90",
        ],
                                            install: true,
    link_language: 'fortran',
    subdir: 'wagl'
    ),
    _sat_sol_angles = py3.extension_module("_sat_sol_angles",
        [
            "f90_sources/sys_variables.f90",
            "f90_sources/solar_angle.f90",
            "f90_sources/geod2geo.f90",
            "f90_sources/q_cal.f90",
            "f90_sources/compute_angles.f90",
            "f90_sources/satellite_solar_angles_main.f90",
        ],
                                           install: true,
    link_language: 'fortran',
    subdir: 'wagl'
    ),
    _bilinear_interpolation = py3.extension_module("_bilinear_interpolation",
        [
            "f90_sources/bilinear_interpolation.f90",
        ],
                                                   install: true,
    link_language: 'fortran',
    subdir: 'wagl'
    )

    return config
