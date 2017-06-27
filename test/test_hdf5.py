#!/usr/bin/env python

"""Test the various utilites contained in the gaip.hdf5 module."""

import datetime
import unittest

import h5py
import numpy as np

from gaip import hdf5


class HDF5Test(unittest.TestCase):
    """Test the various utilites contained in the gaip.hdf5 module."""

    scalar_data = 66
    image_data = np.random.randint(0, 256, (10, 10))
    table_dtype = np.dtype([("float_data", "float64"), ("integer_data", "int64")])
    table_data = np.zeros((10), dtype=table_dtype)
    table_data["float_data"] = np.random.ranf(10)
    table_data["integer_data"] = np.random.randint(0, 10001, (10))

    default_kwargs = {
        "compression": "lzf",
        "shuffle": True,
        "chunks": True,
        "compression_opts": None,
    }

    mafisc_kwargs = {
        "compression": 32002,
        "shuffle": False,
        "chunks": True,
        "compression_opts": (1, 0),
    }

    bitshuffle_kwargs = {
        "compression": 32008,
        "shuffle": False,
        "chunks": True,
        "compression_opts": (0, 2),
    }

    memory_kwargs = {"driver": "core", "backing_store": False}

    def test_default_filter(self):
        """Test the default compression keyword settings."""
        kwargs = hdf5.dataset_compression_kwargs()
        self.assertDictEqual(kwargs, self.default_kwargs)

    def test_mafisc_filter(self):
        """Test the mafisc compression keyword settings."""
        kwargs = hdf5.dataset_compression_kwargs(compression="mafisc")
        self.assertDictEqual(kwargs, self.mafisc_kwargs)

    def test_bitshuffle_filter(self):
        """Test the bitshuffle compression keyword settings."""
        kwargs = hdf5.dataset_compression_kwargs(compression="bitshuffle")
        self.assertDictEqual(kwargs, self.bitshuffle_kwargs)

    def test_scalar_dataset(self):
        """Test the read and write functionality for scalar datasets."""
        attrs = {"test_attribute": "this is a scalar"}
        data = {"value": self.scalar_data, "CLASS": "SCALAR", "VERSION": "0.1"}

        # insert the attribute into the data dict
        for k, v in data.items():
            data[k] = v

        fname = "test_scalar_dataset.h5"
        with h5py.File(fname, **self.memory_kwargs) as fid:
            hdf5.write_scalar(data["value"], "test-scalar", fid, attrs=attrs)

            self.assertDictEqual(hdf5.read_scalar(fid, "test-scalar"), data)

    def test_datetime_attrs(self):
        """Test that datetime objects will be converted to iso format
        when writing attributes.
        """
        attrs = {"timestamp": datetime.datetime.now()}

        fname = "test_datetime_attrs.h5"
        with h5py.File(fname, **self.memory_kwargs) as fid:
            hdf5.write_scalar(self.scalar_data, "scalar", fid, attrs=attrs)

            data = hdf5.read_scalar(fid, "scalar")
            assert data["timestamp"] == attrs["timestamp"].isoformat()

    def test_attach_attributes(self):
        """Test the attach_attributes function."""
        attrs = {"alpha": 1, "beta": 2}

        fname = "test_attach_attributes.h5"
        with h5py.File(fname, **self.memory_kwargs) as fid:
            dset = fid.create_dataset("data", data=self.image_data)
            hdf5.attach_attributes(dset, attrs)
            test = {k: v for k, v in dset.attrs.items()}
            self.assertDictEqual(test, attrs)

    def test_attach_image_attributes(self):
        """Test the attach_image_attributes function."""
        attrs = {"CLASS": "IMAGE", "IMAGE_VERSION": "1.2", "DISPLAY_ORIGIN": "UL"}

        fname = "test_attach_image_attributes.h5"
        with h5py.File(fname, **self.memory_kwargs) as fid:
            dset = fid.create_dataset("data", data=self.image_data)
            hdf5.attach_image_attributes(dset, attrs)
            test = {k: v for k, v in dset.attrs.items()}
            self.assertDictEqual(test, attrs)

    def test_write_h5_image_attributes(self):
        """Test the image attributes of the write_h5_image function."""
        minmax = np.array([self.image_data.min(), self.image_data.max()])
        attrs = {
            "CLASS": "IMAGE",
            "IMAGE_VERSION": "1.2",
            "DISPLAY_ORIGIN": "UL",
            "IMAGE_MINMAXRANGE": minmax,
        }

        fname = "test_write_h5_image_attributes.h5"
        with h5py.File(fname, **self.memory_kwargs) as fid:
            hdf5.write_h5_image(self.image_data, "image", fid)
            test = {k: v for k, v in fid["image"].attrs.items()}
            self.assertDictEqual(test, attrs)

    def test_attach_table_attributes(self):
        """Test the attach_table_attributes function."""
        attrs = {
            "CLASS": "TABLE",
            "IMAGE_VERSION": "0.2",
            "TITLE": "Table",
            "FIELD_0_NAME": "float_data",
            "FIELD_1_NAME": "integer_data",
        }

        fname = "test_attach_table_attributes.h5"
        with h5py.File(fname, **self.memory_kwargs) as fid:
            dset = fid.create_dataset("data", data=self.table_data)
            hdf5.attach_table_attributes(dset, attrs=attrs)
            test = {k: v for k, v in dset.attrs.items()}
            self.assertDictEqual(test, attrs)


if __name__ == "__main__":
    unittest.main()
