
#    config = Configuration('wagl', parent_package, top_path)
#    config.add_subpackage('scripts')
#    config.add_data_files('acquisition/sensors.json')
#    config.add_data_dir('spectral_response')


incdir_numpy = run_command(
    py3,
    ['-c', 'import numpy; print(numpy.get_include())'],
    check: true,
).stdout().strip()
inc_np = include_directories(incdir_numpy)
# np_dep = declare_dependency(include_directories: inc_np)
incdir_f2py = incdir_numpy / '..' / '..' / 'f2py' / 'src'
inc_f2py = include_directories(incdir_f2py)

# Share this object across multiple modules.
fortranobject_lib = static_library(
    '_fortranobject',
    incdir_f2py / 'fortranobject.c',
    # c_args: numpy_nodepr_api,
    dependencies: py3_dep,
    include_directories: [inc_np, inc_f2py],
)
fortranobject_dep = declare_dependency(
    link_with: fortranobject_lib,
    include_directories: [inc_np, inc_f2py],
)

sat_sol_angles_src = [
    'f90_sources/sys_variables.f90',
    'f90_sources/solar_angle.f90',
    'f90_sources/geod2geo.f90',
    'f90_sources/q_cal.f90',
    'f90_sources/compute_angles.f90',
    'f90_sources/satellite_solar_angles_main.f90',
]
_sat_sol_angles_module = custom_target(
    'sat_sol_angles_module',
    input: sat_sol_angles_src,
    output: ['__sat_sol_anglesmodule.c', '__sat_sol_angles-f2pywrappers2.f90'],
    command: [
        'f2py',
        '-m', '__sat_sol_angles',
        '@INPUT@',
        '--build-dir', '@OUTDIR@',
    ],
)
_sat_sol_angles = py3.extension_module(
    '__sat_sol_angles',
    [
        _sat_sol_angles_module,
        sat_sol_angles_src,
    ],
    install: true,
    dependencies: [fortranobject_dep],
    link_language: 'fortran',
    subdir: 'wagl',
)


_cast_shadow_mask = py3.extension_module(
    '__cast_shadow_mask',
    [
        'f90_sources/sys_variables.f90',
        'f90_sources/cast_shadow_main.f90',
        'f90_sources/terrain_border_margins.f90',
        'f90_sources/cast_shadow_mask.f90',
        'f90_sources/terrain_occlusion.f90',
        'f90_sources/geo2metres_pixel_size.f90',
    ],
    install: true,
    link_language: 'fortran',
    subdir: 'wagl',
)
_exiting_angle = py3.extension_module(
    '__exiting_angle',
    [
        'f90_sources/sys_variables.f90',
        'f90_sources/exiting_angle.f90',
        'f90_sources/earth_rotation.f90',
    ],
    install: true,
    link_language: 'fortran',
    subdir: 'wagl',
)
_incident_angle = py3.extension_module(
    '__incident_angle',
    [
        'f90_sources/incident_angle.f90',
        'f90_sources/earth_rotation.f90',
    ],
    install: true,
    link_language: 'fortran',
    subdir: 'wagl',
)
_slope_aspect = py3.extension_module(
    '__slope_aspect',
    [
        'f90_sources/sys_variables.f90',
        'f90_sources/slope_aspect.f90',
        'f90_sources/geo2metres_pixel_size.f90',
    ],
    install: true,
    link_language: 'fortran',
    subdir: 'wagl',
)
_surface_reflectance = py3.extension_module(
    '__surface_reflectance',
    [
        'f90_sources/surface_reflectance.f90',
        'f90_sources/white_sky.f90',
        'f90_sources/black_sky.f90',
        'f90_sources/brdf_shape.f90',
    ],
    install: true,
    link_language: 'fortran',
    subdir: 'wagl',
)
_satellite_model = py3.extension_module(
    '__satellite_model',
    [
        'f90_sources/sys_variables.f90',
        'f90_sources/geo2metres_pixel_size.f90',
        'f90_sources/satellite_model.f90',
    ],
    install: true,
    link_language: 'fortran',
    subdir: 'wagl',
)
_track_time_info = py3.extension_module(
    '__track_time_info',
    [
        'f90_sources/sys_variables.f90',
        'f90_sources/geod2geo.f90',
        'f90_sources/q_cal.f90',
        'f90_sources/geo2metres_pixel_size.f90',
        'f90_sources/satellite_track.f90',
        'f90_sources/track_time_info.f90',
    ],
    install: true,
    link_language: 'fortran',
    subdir: 'wagl',
)


_bilinear_interpolation = py3.extension_module(
    '__bilinear_interpolation',
    [
        'f90_sources/bilinear_interpolation.f90',
    ],
    install: true,
    link_language: 'fortran',
    subdir: 'wagl',
)
