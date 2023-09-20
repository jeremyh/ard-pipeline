# Register hdf5 plugins globally.
# For all usage of h5py.
import hdf5plugin  # noqa: F401

from . import _version as version_module

__version__ = _version = version_module.__version__

__all__ = ("__version__", "_version")
