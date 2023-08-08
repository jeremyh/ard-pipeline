import unittest

from data import LAND_SEA_RASTERS, LS7_SCENE1, LS8_SCENE1

from wagl.acquisition import acquisitions
from wagl.land_sea_masking import calc_land_sea_mask


class LandSeaMaskingTest(unittest.TestCase):
    def test_land_sea_cal(self):
        """Check calc_land_sea_mask for similar result."""
        precomputed_mean = 0.8835457063711911
        geobox = acquisitions(LS8_SCENE1).get_all_acquisitions()[0].gridded_geo_box()
        land_sea_mask, metadata = calc_land_sea_mask(
            geobox, ancillary_path=LAND_SEA_RASTERS
        )
        self.assertAlmostEqual(land_sea_mask.mean(), precomputed_mean, places=2)
        assert isinstance(metadata, dict)

    def test_missing_utm_file(self):
        """Test assertion is raised on missing utm file."""
        geobox = acquisitions(LS7_SCENE1).get_all_acquisitions()[0].gridded_geo_box()
        with self.assertRaises(AssertionError):
            calc_land_sea_mask(geobox, ancillary_path=LAND_SEA_RASTERS)
