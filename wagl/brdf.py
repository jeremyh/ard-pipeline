#!/usr/bin/env python

"""BRDF data extraction utilities
------------------------------.

The :ref:`nbar-algorithm-label` and :ref:`tc-algorithm-label` algorithms
require estimates of various atmospheric parameters, which are produced using
`MODTRAN <http://modtran5.com/>`_. MODTRAN, in turn, requires `BRDF
<http://en.wikipedia.org/wiki/Bidirectional_reflectance_distribution_function>`_
estimates. The estimates used in the ULA, are based on `MODIS
<http://modis.gsfc.nasa.gov/>`_ and are produced by CSIRO. For more
information, on how these are used, see :download:`this
<auxiliary/li_etal_2010_05422912.pdf>`.

`MODIS <http://modis.gsfc.nasa.gov/>`_, pre Feb 2001, MODIS data was not
available and an alternative method of deriving `BRDF
<http://en.wikipedia.org/wiki/Bidirectional_reflectance_distribution_function>`_
estimates is required.

"""

import datetime
import logging
import os
from os.path import join as pjoin
from typing import Dict, List, Literal, Tuple, TypedDict

import h5py
import numpy as np
import pyproj
import rasterio
import shapely
import shapely.affinity
import shapely.geometry
from osgeo import ogr
from rasterio.crs import CRS
from rasterio.features import rasterize
from shapely import ops, wkt
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from wagl.acquisition import Acquisition
from wagl.constants import BrdfDirectionalParameters, BrdfModelParameters, BrdfTier
from wagl.data import read_subset
from wagl.hdf5 import VLEN_STRING, H5CompressionFilter
from wagl.metadata import current_h5_metadata

_LOG = logging.getLogger(__name__)


# Accurate BRDF requires both Terra and Aqua to be operating
# Aqua launched 2002-05-04, so we'll add a buffer for determining the start
# date for using definitive data.
DEFINITIVE_START_DATE = datetime.datetime(2002, 7, 1).date()


class BrdfBandDict(TypedDict):
    iso: float
    vol: float
    geo: float


class BrdfDict(TypedDict):
    #: Optionally, use this user-specified value instead of looking up the data.
    #: (A dict of band-aliases-names-to-value.)
    user: Dict[str, BrdfBandDict]

    #: Base BRDF directory.
    #: Eg. '/g/data/v10/eoancillarydata-2/BRDF/MCD43A1.061'
    #:
    #: This dir should contain H5 files inside day subdirectories:
    #: Eg. '2011.01.29/MCD43A1.A2011014.h29v11.061.2021181032509.h5'
    brdf_path: str

    #: The fallback brdf directory.
    #: Eg. '/g/data/v10/eoancillarydata-2/BRDF_FALLBACK/MCD43A1.006'
    #:
    #: This dir should contain a h5 files in subdirectories for each day-of-year.
    #: Eg. '176/MCD43A1.JLAV.006.h30v10.DOY.176.h5'
    brdf_fallback_path: str

    #: Single ocean mask file.
    #: Eg. '/g/data/v10/eoancillarydata-2/ocean_mask/base_oz_tile_set_water_mask_geotif.tif'
    ocean_mask_path: str


class BRDFLoaderError(Exception):
    """BRDF Loader Error."""


class BRDFLookupError(Exception):
    """BRDF Lookup Error."""


def _date_proximity(cmp_date, date_interpreter=lambda x: x):
    """_date_proximity providers a comparator for an interable
    with an interpreter function. Used to find the closest item
    in a list.

    If two dates are equidistant return the most recent.

    :param cmp_date: date to compare list against
    :param date_interprater: function applied to the list to
        transform items into dates
    """

    def _proximity_comparator(date):
        _date = date_interpreter(date)
        return (
            abs(_date - cmp_date),
            -1 * _date.year,
            -1 * _date.month,
            -1 * _date.day,
        )

    return _proximity_comparator


def get_brdf_dirs_modis(
    brdf_root_dir: str, scene_date: datetime.date, pattern="%Y.%m.%d"
):
    """Get list of MODIS BRDF directories for the dataset.

    A Brdf root directory contains a list of day directories:
        MCD43A1.061/2011.01.14/MCD43A1.A2011014.h29v10.061.2021181032544.h5

    :param pattern:
        A string handed to strptime to interpret directory names into
        observation dates for the brdf ancillary.

    :return:
       A string containing the closest matching BRDF directory name inside the brdf root..

    """
    dirs = []
    for dname in sorted(os.listdir(brdf_root_dir)):
        try:
            dirs.append(datetime.datetime.strptime(dname, pattern).date())
        except ValueError:
            pass  # Ignore directories that don't match specified pattern

    return min(dirs, key=_date_proximity(scene_date)).strftime(pattern)


def get_brdf_dirs_fallback(brdf_root: str, scene_date: datetime.date) -> str:
    """Get list of pre-MODIS BRDF directories for the dataset.

    :param brdf_root:
        BRDF root directory.
    :type brdf_root:
        :py:class:`str`

    :param scene_date:
        Scene Date.
    :type scene_date:
        :py:class:`datetime.date`

    :return:
       A string containing the closest matching BRDF directory.

    """
    # Find the N (=n_dirs) BRDF directories with midpoints closest to the
    # scene date.
    # Pre-MODIS BRDF directories are named 'XXX' (day-of-year).
    # Return a list of n_dirs directories to maintain compatibility with
    # the NBAR code, even though we know that the nearest day-of-year
    # database dir will contain usable data.
    # Build list of dates for comparison
    dir_dates = []

    # Standardise names be prepended with leading zeros
    for doy in sorted(os.listdir(brdf_root), key=lambda x: x.zfill(3)):
        dir_dates.append((str(scene_date.year), doy))

    # Add boundary entry for previous year
    dir_dates.insert(0, (str(scene_date.year - 1), dir_dates[-1][1]))
    # Add boundary entry for next year accounting for inserted entry
    dir_dates.append((str(scene_date.year + 1), dir_dates[1][1]))

    # return directory name without year
    return min(
        dir_dates,
        key=_date_proximity(
            scene_date,
            lambda x: datetime.datetime.strptime(" ".join(x), "%Y %j").date(),
        ),
    )[1]


def coord_transformer(src_crs, dst_crs):
    """Coordinate transformation function between CRSs.

    :param src_crs:
        Source CRS.
    :type src_crs:
        :py:class:`rasterio.crs.CRS`

    :param dst_crs:
        Destination CRS.
    :type dst_crs:
        :py:class:`rasterio.crs.CRS`

    :return:
        A function that takes a point in the source CRS and returns the same
        point expressed in the destination CRS.
    """

    def crs_to_proj(crs):
        return pyproj.Proj(**crs.to_dict())

    def result(*args, **kwargs):
        return pyproj.transform(
            crs_to_proj(src_crs), crs_to_proj(dst_crs), *args, **kwargs
        )

    return result


class BrdfSummaryDict(TypedDict):
    sum: float
    count: int


class BrdfValue(TypedDict):
    # The source brdf files.
    id: List[str]
    # The value.
    value: float


class BrdfTileSummary:
    """A lightweight class to represent the BRDF information gathered from a tile."""

    def __init__(
        self,
        brdf_summaries: Dict[BrdfModelParameters, BrdfSummaryDict],
        source_ids: List[str],
        source_files: List[str],
    ):
        self.brdf_summaries = brdf_summaries
        self.source_ids = source_ids
        self.source_files = source_files

    @staticmethod
    def empty():
        """When the tile is not inside the ROI."""
        return BrdfTileSummary(
            {key: BrdfSummaryDict(sum=0.0, count=0) for key in BrdfModelParameters},
            [],
            [],
        )

    def is_empty(self) -> bool:
        return all(
            self.brdf_summaries[key]["count"] == 0 for key in BrdfModelParameters
        )

    def __add__(self, other: "BrdfTileSummary"):
        """Accumulate information from different tiles."""

        def add(key):
            this = self.brdf_summaries[key]
            that = other.brdf_summaries[key]
            return BrdfSummaryDict(
                sum=this["sum"] + that["sum"], count=this["count"] + that["count"]
            )

        return BrdfTileSummary(
            {key: add(key) for key in BrdfModelParameters},
            sorted(set(self.source_files + other.source_files)),
            sorted(set(self.source_ids + other.source_ids)),
        )

    def mean(self) -> Dict[BrdfDirectionalParameters, BrdfValue]:
        """Calculate the mean BRDF parameters."""
        if self.is_empty():
            # possibly over the ocean, so lambertian
            return {
                key: BrdfValue(id=self.source_ids, value=0.0)
                for key in BrdfDirectionalParameters
            }

        # ratio of spatial averages
        averages = {
            key: self.brdf_summaries[key]["sum"] / self.brdf_summaries[key]["count"]
            for key in BrdfModelParameters
        }

        bands = {
            BrdfDirectionalParameters.ALPHA_1: BrdfModelParameters.VOL,
            BrdfDirectionalParameters.ALPHA_2: BrdfModelParameters.GEO,
        }

        return {
            key: BrdfValue(
                id=self.source_ids,
                value=averages[bands[key]] / averages[BrdfModelParameters.ISO],
            )
            for key in BrdfDirectionalParameters
        }


def valid_region(acquisition, mask_value=None) -> Tuple[BaseGeometry, dict]:
    """Return valid data region for input images based on mask value and input image path."""
    img = acquisition.data()
    gbox = acquisition.gridded_geo_box()
    crs = CRS.from_wkt(gbox.crs.ExportToWkt()).to_dict()
    transform = gbox.transform.to_gdal()

    if mask_value is None:
        mask_value = acquisition.no_data

    if mask_value is not None:
        mask = img != mask_value
    else:
        mask = img != 0

    shapes = rasterio.features.shapes(mask.astype("uint8"), mask=mask)
    shape: BaseGeometry = ops.unary_union(
        [shapely.geometry.shape(shape) for shape, val in shapes if val == 1]
    )

    geom: BaseGeometry = shape.convex_hull

    # buffer by 1 pixel
    geom = geom.buffer(1, join_style=3, cap_style=3)

    # simplify with 1 pixel radius
    geom = geom.simplify(1)

    # intersect with image bounding box
    geom = geom.intersection(shapely.geometry.box(0, 0, mask.shape[1], mask.shape[0]))

    # transform from pixel space into CRS space
    geom = shapely.affinity.affine_transform(
        geom,
        (
            transform[1],
            transform[2],
            transform[4],
            transform[5],
            transform[0],
            transform[3],
        ),
    )

    return geom, crs


def load_brdf_tile(
    src_poly,
    src_crs,
    fid: h5py.File,
    dataset_name: str,
    fid_mask: rasterio.DatasetReader,
) -> BrdfTileSummary:
    """Summarize BRDF data from a single tile."""
    ds = fid[dataset_name]

    def segmentize_src_poly(length_scale):
        src_poly_geom = ogr.CreateGeometryFromWkt(src_poly.wkt)
        src_poly_geom.Segmentize(length_scale)
        return wkt.loads(src_poly_geom.ExportToWkt())

    ds_height, ds_width = ds.shape

    dst_geotransform = rasterio.transform.Affine.from_gdal(*ds.attrs["geotransform"])
    dst_crs = CRS.from_wkt(ds.attrs["crs_wkt"])

    # assumes the length scales are the same (m)
    dst_poly = ops.transform(
        coord_transformer(src_crs, dst_crs),
        segmentize_src_poly(np.sqrt(np.abs(dst_geotransform.determinant))),
    )

    bound_poly = ops.transform(
        lambda x, y: dst_geotransform * (x, y),
        box(0.0, 0.0, ds_width, ds_height, ccw=False),
    )
    if not bound_poly.intersects(dst_poly):
        return BrdfTileSummary.empty()

    ocean_poly = ops.transform(
        lambda x, y: fid_mask.transform * (x, y),
        box(0.0, 0.0, fid_mask.width, fid_mask.height),
    )
    if not ocean_poly.intersects(dst_poly):
        return BrdfTileSummary.empty()

    # read ocean mask file for correspoing tile window
    # land=1, ocean=0
    bound_poly_coords = list(bound_poly.exterior.coords)[:4]
    ocean_mask, _ = read_subset(fid_mask, *bound_poly_coords)
    ocean_mask = ocean_mask.astype(bool)

    # inside=1, outside=0
    roi_mask = rasterize(
        [(dst_poly, 1)],
        fill=0,
        out_shape=(ds_height, ds_width),
        transform=dst_geotransform,
    )
    roi_mask = roi_mask.astype(bool)

    # both ocean_mask and mask shape should be same
    if ocean_mask.shape != roi_mask.shape:
        raise ValueError("ocean mask and ROI mask do not have the same shape")
    if roi_mask.shape != ds.shape:
        raise ValueError("BRDF dataset and ROI mask do not have the same shape")

    roi_mask = roi_mask & ocean_mask

    def layer_sum(param):
        layer = ds[param][:, :]
        common_mask = roi_mask & (layer != ds.attrs["_FillValue"])
        layer = layer.astype("float32")
        layer[~common_mask] = np.nan
        layer = ds.attrs["scale_factor"] * (layer - ds.attrs["add_offset"])
        return {"sum": np.nansum(layer), "count": np.sum(common_mask)}

    return BrdfTileSummary(
        {param: layer_sum(param.value) for param in BrdfModelParameters},
        [current_h5_metadata(fid)["id"]],
        [fid.filename],
    )


class NoBrdfRootError(ValueError):
    """
    The configured BRDF folder doesn't exist, or has no data.

    This is a hard error if you have specified a BRDF directory.
    """

    ...


AncillaryTier = Literal["DEFINITIVE", "FALLBACK_DATASET"]


class LoadedBrdfCoverageDict(TypedDict):
    data_source: Literal["BRDF"]
    local_source_paths: List[str]
    tier: AncillaryTier
    id: np.ndarray[str]
    value: float


def get_brdf_data(
    acquisition: Acquisition,
    brdf: BrdfDict,
    compression=H5CompressionFilter.LZF,
    filter_opts=None,
) -> Dict[BrdfDirectionalParameters, LoadedBrdfCoverageDict]:
    """Calculates the mean BRDF value for the given acquisition,
    for each BRDF parameter ['geo', 'iso', 'vol'] that covers
    the acquisition's extents.

    :param acquisition:
        An instance of an acquisitions object.

    :param brdf:
        A `dict` defined as either of the following:
        * {'user': {<band-alias>: {'iso': <value>, 'vol': <value>, 'geo': <value>}, ...}}
        * {'brdf_path': <path-to-BRDF>, 'brdf_fallback_path': <path-to-average-BRDF>,
           'ocean_mask_path': <path-to-ocean-mask>}

        Here <path-to-BRDF> is a string containing the full file system
        path to your directory containing the ource BRDF files
        The BRDF directories are assumed to be yyyy.mm.dd naming convention.

        <path-to-average-BRDF> is a string containing the full file system
        path to your directory containing the fallback BRDF data.
        To be used for pre-MODIS and potentially post-MODIS acquisitions.

        And <path-to-ocean-mask> is a string containing the full file system path
        to your ocean mask file. To be used for masking ocean pixels from  BRDF data
        all acquisitions.

    :param compression:
        The compression filter to use.
        Default is H5CompressionFilter.LZF

    :filter_opts:
        A dict of key value pairs available to the given configuration
        instance of H5CompressionFilter. For example
        H5CompressionFilter.LZF has the keywords *chunks* and *shuffle*
        available.
        Default is None, which will use the default settings for the
        chosen H5CompressionFilter instance.

    :return:
        A `dict` with the keys:

            * BrdfDirectionalParameters.ALPHA_1
            * BrdfDirectionalParameters.ALPHA_2

        Values for each BRDF Parameter are accessed via the key named
        `value`.

    :notes:
        The keywords compression and filter_opts aren't used as we no
        longer save the BRDF imagery. However, we may need to store
        tables in future, therefore they can remain until we know
        for sure they'll never be used.
    """
    if "user" in brdf:
        # user-specified override
        return {
            param: {
                "data_source": "BRDF",
                "tier": BrdfTier.USER.name,
                "value": brdf["user"][acquisition.alias][param.value.lower()],
            }
            for param in BrdfDirectionalParameters
        }

    brdf_primary_path = brdf["brdf_path"]
    brdf_secondary_path = brdf["brdf_fallback_path"]
    brdf_ocean_mask_path = brdf["ocean_mask_path"]

    src_poly, src_crs = valid_region(acquisition)
    src_crs = rasterio.crs.CRS(**src_crs)

    brdf_datasets: List[str] = acquisition.brdf_datasets

    # Get the date of acquisition
    dt = acquisition.acquisition_datetime.date()

    # Have they provided a BRDF path?
    if brdf_primary_path:
        # If they specified a directory that doesn't exist, that's a system error.
        # But if the date is outside our available range, go to fallback brdf.
        if not os.path.isdir(brdf_primary_path):
            raise NoBrdfRootError(
                f"No BRDF dir found on system. Expecting {brdf_primary_path!r}"
            )
        brdf_dirs = os.listdir(brdf_primary_path)
        if not brdf_dirs:
            raise NoBrdfRootError(
                f"No BRDF data found on system. Expecting inside {brdf_primary_path!r}"
            )

        # Compare the scene date and MODIS BRDF date to select the BRDF directory.
        last_brdf_dir = sorted(brdf_dirs)[-1]
        last_brdf_date = datetime.date(*[int(x) for x in last_brdf_dir.split(".")])
        use_fallback_brdf = (dt < DEFINITIVE_START_DATE) or (dt > last_brdf_date)
    else:
        use_fallback_brdf = True

    def get_tally(
        use_fallback_brdf: bool, dt: datetime.datetime
    ) -> Dict[str, BrdfTileSummary]:
        # get all HDF files in the input dir
        if use_fallback_brdf:
            brdf_base_dir = brdf_secondary_path
            brdf_day_dir = get_brdf_dirs_fallback(brdf_base_dir, dt)
        else:
            brdf_base_dir = brdf_primary_path
            brdf_day_dir = get_brdf_dirs_modis(brdf_base_dir, dt)

        dbDir = pjoin(brdf_base_dir, brdf_day_dir)
        tile_list = [
            pjoin(folder, f)
            for (folder, _, filelist) in os.walk(dbDir)
            for f in filelist
            if f.endswith(".h5")
        ]

        tally: Dict[str, BrdfTileSummary] = {}
        with rasterio.open(brdf_ocean_mask_path, "r") as fid_mask:
            for ds in brdf_datasets:
                tally[ds] = BrdfTileSummary.empty()
                for tile in tile_list:
                    with h5py.File(tile, "r") as fid:
                        tally[ds] += load_brdf_tile(
                            src_poly, src_crs, fid, ds, fid_mask
                        )
        return tally

    tally = get_tally(use_fallback_brdf, dt)

    def is_empty(tally):
        return any(tally[ds].is_empty() for ds in brdf_datasets)

    days_back = 0
    while not use_fallback_brdf and is_empty(tally):
        if days_back > 30:
            tally = get_tally(True, dt)
            break

        days_back += 1
        tally = get_tally(use_fallback_brdf, dt - datetime.timedelta(days=days_back))

    dataset_tallies = {ds: tally[ds].mean() for ds in brdf_datasets}

    return {
        param: LoadedBrdfCoverageDict(
            data_source="BRDF",
            id=np.array(
                list(
                    {
                        ds_id
                        for ds in brdf_datasets
                        for ds_id in dataset_tallies[ds][param]["id"]
                    }
                ),
                dtype=VLEN_STRING,
            ),
            local_source_paths=[
                path for ds in brdf_datasets for path in tally[ds].source_files
            ],
            value=np.mean(
                [dataset_tallies[ds][param]["value"] for ds in brdf_datasets]
            ).item(),
            tier=(
                BrdfTier.FALLBACK_DATASET.name
                if use_fallback_brdf
                else BrdfTier.DEFINITIVE.name
            ),
        )
        for param in BrdfDirectionalParameters
    }
