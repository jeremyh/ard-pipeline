project('ard-pipeline', 'c', 'fortran')

py_mod = import('python')
py3 = py_mod.find_installation(pure: false)
py3_dep = py3.dependency()


c = run_command('utils/py-files.sh', check: true)
python_sources = c.stdout().strip().split('\n')
py3.install_sources(
    python_sources,
    preserve_path: true,
)

subdir('wagl')
