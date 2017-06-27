import os
import unittest

import gaip

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

NBAR_DIR_LS5 = os.path.join(
    DATA_DIR, "NBAR", "2009-01", "LS5_TM_NBAR_P54_GANBAR01-002_092_086_20090115"
)
NBAR_DIR_LS7 = os.path.join(
    DATA_DIR, "NBAR", "2004-03", "LS7_ETM_NBAR_P54_GANBAR01-002_112_083_20040311"
)
NBAR_DIR_LS8 = os.path.join(
    DATA_DIR, "NBAR", "2013-06", "LS8_OLI_TIRS_NBAR_P54_GANBAR01-032_090_082_20130605"
)


class AcquisitionTest(unittest.TestCase):
    def test_load_acquisitions(self):
        acqs = gaip.acquisitions(NBAR_DIR_LS5)
        assert len(acqs) == 6

    def test_acquisition(self):
        acq = gaip.acquisitions(NBAR_DIR_LS5)[0]

        assert isinstance(acq, gaip.Landsat5Acquisition)

        assert acq.band_type == gaip.REF
        assert acq.band_name == "band1"
        assert acq.band_num == 1

        assert not hasattr(acq, "band1_sl_gain_change")
        assert acq.sensor_id == "TM"
        assert acq.no_data == -999, "no_data value should be -999"

    def test_acquisition_LS7(self):
        acqs = gaip.acquisitions(NBAR_DIR_LS7)
        assert len(acqs) == 6

        acq = acqs[0]
        assert isinstance(acq, gaip.Landsat7Acquisition)
        assert acq.band_type == gaip.REF
        assert acq.band_name == "band1"
        assert acq.band_num == 1

        acq = acqs[5]
        assert acq.band_name == "band7"
        assert acq.band_num == 7
        assert acq.sensor_id == "ETM+"
        assert acq.no_data == -999, "no_data value should be -999"

    def test_acquisition_LS8(self):
        acqs = gaip.acquisitions(NBAR_DIR_LS8)

        acq = acqs[0]
        assert isinstance(acq, gaip.Landsat8Acquisition)
        assert acq.band_type == gaip.REF
        assert acq.band_name == "band1"
        assert acq.band_num == 1

        acq = acqs[6]
        assert acq.band_name == "band7"
        assert acq.band_num == 7
        assert acq.sensor_id == "OLI_TIRS"
        assert acq.no_data == -999, "no_data value should be -999"

    def test_acquisition_LS5(self):
        acqs = gaip.acquisitions(NBAR_DIR_LS5)

        acq = acqs[0]
        assert isinstance(acq, gaip.Landsat5Acquisition)
        assert acq.band_type == gaip.REF
        assert acq.band_name == "band1"
        assert acq.band_num == 1

        acq = acqs[1]
        assert acq.band_type == gaip.REF
        assert acq.band_name == "band2"
        assert acq.band_num == 2
        assert acq.sensor_id == "TM"
        assert acq.no_data == -999, "no_data value should be -999"

    def test_acquisition_LS8_no_data(self):
        acqs = gaip.acquisitions(NBAR_DIR_LS8)
        acq = acqs[0]
        assert isinstance(acq, gaip.Landsat8Acquisition)
        assert acq.band_type == gaip.REF
        assert acq.no_data == -999, "no_data value should be -999"

    def test_single_band_read(self):
        acqs = gaip.acquisitions(NBAR_DIR_LS5)
        acq = acqs[0]
        band_data = acq.data()
        assert band_data.shape == (8561, 9641)

    def no_test_single_band_read_with_gridded_geo_box(self):
        acq = self.acqs[0]
        band_data, box = acq.data_and_box()
        assert band_data.shape == (9081, 9401)
        assert type(box) == gaip.GriddedGeoBox
        assert box.origin == (644000.0, 6283000.0)
        assert box.corner == (879025.0, 6055975.0)
        assert box.shape == (9081, 9401)
        assert box.pixelsize == (25.0, 25.0)

    def test_LS5_stack_read(self):
        acqs = gaip.acquisitions(NBAR_DIR_LS5)
        (acqs_read, stack, geobox) = gaip.stack_data(
            acqs, filter=(lambda acq: acq.band_type == gaip.REF)
        )
        assert stack.shape == (6, 8561, 9641)


if __name__ == "__main__":
    unittest.main()
