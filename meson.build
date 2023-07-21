project('ard-pipeline', 'fortran',
  default_options : ['warning_level=3'])

py_mod = import('python')
py = py_mod.find_installation(pure: false)

py.extension_module(
    'our_first_module',
    'our_first_module.c',
    install: true,
)

subdir('wagl')
