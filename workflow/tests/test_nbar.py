import logging
import os
import unittest
from os.path import dirname
from os.path import join as pjoin

import luigi

import gaip
import workflow

L1T_PATH = pjoin(dirname(gaip.__file__), "tests", "data", "L1T")
LS7_PATH = pjoin(
    L1T_PATH,
    "LS7_90-81_2009-04-15",
    "UTM",
    "LS7_ETM_OTH_P51_GALPGS01-002_090_081_20090415",
)


logging.disable(logging.CRITICAL)


class ElevationAncillaryDataTest(unittest.TestCase):
    def setUp(self):
        self.task = workflow.GetElevationAncillaryDataTask(LS7_PATH)

    def test_invoke(self):
        luigi.build([self.task], local_scheduler=True)
        assert os.path.exists(self.task.output().path)

    def test_value(self):
        luigi.build([self.task], local_scheduler=True)
        assert self.task.complete()
        value = workflow.load(self.task.output)
        self.assertAlmostEqual(value["value"], 0.292)


class OzoneAncillaryDataTest(unittest.TestCase):
    def setUp(self):
        self.task = workflow.GetOzoneAncillaryDataTask(LS7_PATH)

    def test_invoke(self):
        luigi.build([self.task], local_scheduler=True)
        assert os.path.exists(self.task.output().path)

    def test_value(self):
        luigi.build([self.task], local_scheduler=True)
        assert self.task.complete()
        value = workflow.load(self.task.output)
        self.assertAlmostEqual(value["value"], 0.26800001)


if __name__ == "__main__":
    unittest.main()
