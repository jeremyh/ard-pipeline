try:
    from importlib import metadata
except ImportError:
    # Running on pre-3.8 Python; use importlib-metadata package
    import importlib_metadata as metadata

try:
    __version__ = metadata.version(__name__)
except metadata.PackageNotFoundError:
    __version__ = "Unpackaged-Install"


# Register hdf5 plugins globally.
# For all usage of h5py.
import hdf5plugin  # noqa: F401
