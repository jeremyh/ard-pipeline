import datetime
import os
import unittest

import gaip

MTL_FILE_DATA = os.path.join(os.path.dirname(__file__), "data", "mtl.txt")


class TypeParserTest(unittest.TestCase):
    def test_integer(self):
        num = gaip.parse_type("1")
        assert num == 1

    def test_float(self):
        num = gaip.parse_type("1.0")
        assert num == 1.0

    def test_datetime(self):
        dt0 = gaip.parse_type("2013-11-07T01:42:41Z")
        dt1 = datetime.datetime(2013, 11, 7, 1, 42, 41)
        assert dt0 == dt1

    def test_date(self):
        dt0 = gaip.parse_type("2013-11-07")
        dt1 = datetime.date(2013, 11, 7)
        assert dt0 == dt1

    def test_time(self):
        dt0 = gaip.parse_type("23:46:09.1442826Z")
        dt1 = datetime.time(23, 46, 9, 144282)
        assert dt0 == dt1

    def test_yes(self):
        resp = gaip.parse_type("Y")
        assert resp is True

    def test_no(self):
        resp = gaip.parse_type("N")
        assert resp is False

    def test_none(self):
        val = gaip.parse_type("NONE")
        assert val is None

    def test_str(self):
        s = gaip.parse_type("1adsd")
        assert s == "1adsd"


class MTLParserTest(unittest.TestCase):
    def test_load(self):
        tree = gaip.load_mtl(MTL_FILE_DATA)
        assert len(tree) == 8
        assert tree.has_key("METADATA_FILE_INFO")
        assert tree.has_key("PRODUCT_METADATA")
        assert tree.has_key("MIN_MAX_RADIANCE")
        assert tree.has_key("MIN_MAX_PIXEL_VALUE")
        assert tree.has_key("PRODUCT_PARAMETERS")
        assert tree.has_key("CORRECTIONS_APPLIED")
        assert tree.has_key("PROJECTION_PARAMETERS")
        assert tree.has_key("UTM_PARAMETERS")


class AcquisitionTest(unittest.TestCase):
    def test_load_acquisitions(self):
        acq = gaip.acquisitions(MTL_FILE_DATA)
        assert len(acq) == 9

    def test_acquisition(self):
        acq = gaip.acquisitions(MTL_FILE_DATA)[0]

        assert acq.band_name == "band1"
        assert acq.band_num == 1
        assert acq.file_name == "L71090084_08420131003_B10.TIF"
        assert acq.lmin == -6.2
        assert acq.lmax == 191.6
        assert acq.qcalmin == 1.0
        assert acq.qcalmax == 255.0

        assert not hasattr(acq, "lmin_band1")
        assert not hasattr(acq, "lmin_band2")

        assert not hasattr(acq, "band1_sl_gain_change")


if __name__ == "__main__":
    unittest.main()
