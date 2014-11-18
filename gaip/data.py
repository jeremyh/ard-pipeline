from os.path import join as pjoin

import rasterio


def data(acq):
    dirname = acq.dir_name
    filename = acq.file_name
    with rasterio.open(pjoin(dirname, filename), "r") as fo:
        return fo.read_band(1)
