# class LandSeaTest(unittest.TestCase):
#     def test_land_sea(self):
#         """
#         Check calc_land_sea_mask for similar result
#         """
#         precomputed_mean = 0.8835457063711911
#         geobox = acquisitions(LS8_SCENE1).get_all_acquisitions()[0].gridded_geo_box()
#         land_sea_mask = get_land_sea_mask(geobox, ancillary_path=LAND_SEA_RASTERS)
#         self.assertAlmostEqual(land_sea_mask.mean(), precomputed_mean, places=2)
