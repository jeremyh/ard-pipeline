#!/bin/env python

# import luigi
import os

import luigi.contrib.mpi as mpi

if __name__ == "__main__":
    outputRoot = os.getenv("OUTPUT_ROOT", "/tmp/smr")

    tasks = []
    with open("NBAR_test_scenes_64.txt") as infile:
        for line in infile:
            nbarPath = line.strip()
            fcName = os.path.basename(nbarPath).replace("NBAR", "FC")
            tasks.append(FractionalCoverTask(nbarPath, f"{outputRoot}/output/{fcName}"))

    mpi.run(tasks)
