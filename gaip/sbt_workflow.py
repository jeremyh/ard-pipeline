#!/usr/bin/env python
"""NBAR Workflow
-------------.

Workflow settings can be configured in `luigi.cfg` file.

"""
# pylint: disable=missing-docstring,no-init,too-many-function-args
# pylint: disable=too-many-locals
# pylint: disable=protected-access

from os.path import basename
from os.path import join as pjoin

import luigi
from luigi.util import requires

from gaip.acquisition import acquisitions
from gaip.nbar_workflow import (
    CalculateLatGrid,
    CalculateLonGrid,
    CalculateSatelliteAndSolarGrids,
    RunModtranCase,
    WriteTp5,
)


@requires(CalculateSatelliteAndSolarGrids)
class ThermalAncillary(luigi.Task):
    """Collect the ancillary data required for SBT."""

    dewpoint_path = luigi.Parameter(significant=False)
    temp_2m_path = luigi.Parameter(significant=False)
    surface_pressure_path = luigi.Parameter(significant=False)
    geopotential_path = luigi.Parameter(significant=False)
    temperature_path = luigi.Parameter(significant=False)
    relative_humidity_path = luigi.Parameter(significant=False)
    invariant_height_fname = luigi.Parameter(significant=False)

    def output(self):
        out_path = acquisitions(self.level1).get_root(
            self.work_root, granule=self.granule
        )
        return luigi.LocalTarget(pjoin(out_path, "sbt-ancillary.h5"))

    def run(self):
        container = acquisitions(self.level1)
        acqs = container.get_acquisitions(granule=self.granule)
        container.get_root(self.work_root, granule=self.granule)

        sat_sol_fname = self.input().path

        with self.output().temporary_path() as out_fname:
            _collect_thermal_ancillary(
                acqs[0],
                sat_sol_fname,
                self.dewpoint_path,
                self.temp_2m_path,
                self.surface_pressure_path,
                self.geopotential_path,
                self.temperature_path,
                self.relative_humidity_path,
                self.invariant_height_fname,
                out_fname,
                self.compression,
            )


class ThermalTp5(WriteTp5):
    """Output the `tp5` formatted files."""

    npoints = luigi.IntParameter(default=25, significant=False)
    albedos = luigi.ListParameter(default=["th"], significant=False)

    def requires(self):
        # for consistancy, we'll wait for dependencies on all granules and
        # groups of acquisitions
        # current method requires to compute an average from all granules
        # if the scene is tiled up that way
        container = acquisitions(self.level1)
        tasks = {}

        for granule in container.granules:
            key1 = (granule, "ancillary")
            args1 = [self.level1, self.work_root, granule]
            tasks[key1] = ThermalAncillary(*args1)
            for group in container.groups:
                key2 = (granule, group)
                args2 = [self.level1, self.work_root, granule, group]
                tsks = {
                    "sat_sol": CalculateSatelliteAndSolarGrids(*args2),
                    "lat": CalculateLatGrid(*args2),
                    "lon": CalculateLonGrid(*args2),
                }
                tasks[key2] = tsks

        return tasks


@requires(ThermalTp5)
class SBTModtranCase(RunModtranCase):
    pass


class SurfaceTemperature(luigi.Task):
    """Calculates surface brightness temperature."""


class SBT(luigi.WrapperTask):
    """Kicks off SurfaceTemperature tasks for each level1 entry."""

    level1_csv = luigi.Parameter()
    output_directory = luigi.Parameter()
    work_extension = luigi.Parameter(default=".gaip-work", significant=False)

    def requires(self):
        with open(self.level1_csv) as src:
            level1_scenes = [scene.strip() for scene in src.readlines()]

        for scene in level1_scenes:
            work_name = basename(scene) + self.work_extension
            work_root = pjoin(self.output_directory, work_name)
            container = acquisitions(scene)
            for granule in container.granules:
                for group in container.groups:
                    yield SurfaceTemperature(scene, work_root, granule, group)


if __name__ == "__main__":
    luigi.run()
