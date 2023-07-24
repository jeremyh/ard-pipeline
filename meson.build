project('ard-pipeline', 'c', 'fortran')

py_mod = import('python')
py3 = py_mod.find_installation(pure: false)
py3_dep = py3.dependency()
ff = meson.get_compiler('fortran')

c = run_command('utils/py-files.sh', check: true)
python_sources = c.stdout().strip().split('\n')
py3.install_sources(
    python_sources,
    preserve_path: true,
)

fortran_args = ff.get_supported_arguments(
    ff.get_supported_arguments('-Wno-argument-mismatch'),
    ff.get_supported_arguments('-Wno-conversion'),
    ff.get_supported_arguments('-Wno-maybe-uninitialized'),
    ff.get_supported_arguments('-Wno-unused-dummy-argument'),
    ff.get_supported_arguments('-Wno-unused-label'),
    ff.get_supported_arguments('-Wno-unused-variable'),
    ff.get_supported_arguments('-Wno-tabs'),
)


subdir('wagl')
