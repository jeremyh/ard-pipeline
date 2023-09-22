# Register hdf5 plugins globally.
# For all usage of h5py.
import hdf5plugin  # noqa: F401

from ._version import __version__

_version = __version__

__all__ = ("__version__", "_version")
