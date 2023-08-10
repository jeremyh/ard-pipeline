import datetime
import unittest

from data import S2A_SCENE1, S2B_SCENE1

from wagl.acquisition import acquisitions
from wagl.acquisition.sentinel import (
    Sentinel2aAcquisition,
    Sentinel2bAcquisition,
)
from wagl.constants import BandType


class AcquisitionLoadZipTest(unittest.TestCase):
    def test_load_acquisitions_s2a_scene1(self):
        container = acquisitions(S2A_SCENE1)

        assert container.granules == [
            "S2A_OPER_MSI_L1C_TL_SGS__20171207T032513_A012840_T55JEJ_N02.06"
        ]

        all_acquisitions = container.get_all_acquisitions()
        assert len(all_acquisitions) == 11
        # Sanity check
        assert sorted(acq.band_name for acq in all_acquisitions) == [
            "BAND-1",
            "BAND-11",
            "BAND-12",
            "BAND-2",
            "BAND-3",
            "BAND-4",
            "BAND-5",
            "BAND-6",
            "BAND-7",
            "BAND-8",
            "BAND-8A",
        ]

        assert len(container.get_acquisitions(group="RES-GROUP-0")) == 4
        assert len(container.get_acquisitions(group="RES-GROUP-1")) == 6
        assert len(container.get_acquisitions(group="RES-GROUP-2")) == 1


class AcquisitionsContainerTestS2(unittest.TestCase):
    def test_groups_s2a_scene1(self):
        container = acquisitions(S2A_SCENE1)
        assert len(container.groups) == 3

    def test_groups_s2b_scene1(self):
        container = acquisitions(S2B_SCENE1)
        assert len(container.groups) == 3

    def test_granules_s2a_scene1(self):
        container = acquisitions(S2A_SCENE1)
        assert len(container.granules) == 1
        assert (
            container.granules[0]
            == "S2A_OPER_MSI_L1C_TL_SGS__20171207T032513_A012840_T55JEJ_N02.06"
        )

    def test_granules_s2b_scene1(self):
        container = acquisitions(S2B_SCENE1)
        assert len(container.granules) == 1
        assert (
            container.granules[0]
            == "S2B_OPER_MSI_L1C_TL_SGS__20170719T012130_A001915_T56JKT_N02.05"
        )


class Sentinel2AScene1AcquisitionTest(unittest.TestCase):
    def setUp(self):
        self.container = acquisitions(S2A_SCENE1)
        self.acq = self.container.get_all_acquisitions()[0]

    def test_type(self):
        for acq in self.container.get_all_acquisitions():
            assert isinstance(acq, Sentinel2aAcquisition)
            assert acq.band_type == BandType.REFLECTIVE

    def test_acquisition_datetime(self):
        test_date = datetime.datetime(2017, 12, 7, 0, 22, 52, 127000)
        for acq in self.container.get_all_acquisitions():
            assert acq.acquisition_datetime == test_date

    def test_sensor_id(self):
        for acq in self.container.get_all_acquisitions():
            assert acq.sensor_id == "MSI"

    def test_platform_id(self):
        for acq in self.container.get_all_acquisitions():
            assert acq.platform_id == "SENTINEL_2A"

    def test_samples(self):
        assert self.acq.samples == 172

    def test_lines(self):
        assert self.acq.lines == 172

    def test_spectral_filter_cfg(self):
        assert self.acq.spectral_filter_name == "sentinel2a_all.flt"

    def test_read(self):
        assert self.acq.data()[70, 30] == 1083

    def test_tzinfo(self):
        for acq in self.container.get_all_acquisitions():
            assert acq.acquisition_datetime, None


class Sentinel2BScene1AcquisitionTest(unittest.TestCase):
    def setUp(self):
        self.container = acquisitions(S2B_SCENE1)
        self.acq = self.container.get_all_acquisitions()[0]

    def test_type(self):
        for acq in self.container.get_all_acquisitions():
            assert isinstance(acq, Sentinel2bAcquisition)
            assert acq.band_type == BandType.REFLECTIVE

    def test_acquisition_datetime(self):
        test_date = datetime.datetime(2017, 7, 19, 0, 2, 18, 457000)
        for acq in self.container.get_all_acquisitions():
            assert acq.acquisition_datetime == test_date

    def test_sensor_id(self):
        for acq in self.container.get_all_acquisitions():
            assert acq.sensor_id == "MSI"

    def test_platform_id(self):
        for acq in self.container.get_all_acquisitions():
            assert acq.platform_id == "SENTINEL_2B"

    def test_samples(self):
        assert self.acq.samples == 172

    def test_lines(self):
        assert self.acq.lines == 172

    def test_spectral_filter_cfg(self):
        assert self.acq.spectral_filter_name == "sentinel2b_all.flt"

    def test_read(self):
        assert self.acq.data()[100, 100] == 2

    def test_tzinfo(self):
        for acq in self.container.get_all_acquisitions():
            assert acq.acquisition_datetime, None
