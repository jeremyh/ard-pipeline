#!/usr/bin/env python

import argparse
from os.path import exists
from os.path import join as pjoin

import numpy as np
import rasterio


def main(ref_dir, test_dir, scenes, files):
    for scene in scenes:
        ref_scene = pjoin(ref_dir, scene)
        test_scene = pjoin(test_dir, scene)
        for f in files:
            ref_fname = pjoin(ref_scene, f)
            test_fname = pjoin(test_scene, f)
            if not exists(ref_fname):
                continue
            with rasterio.open(ref_fname) as ref_ds, rasterio.open(
                test_fname
            ) as test_ds:
                print(f"Testing\nScene: {scene}\n File: {f}")
                diff = ref_ds.read(1).astype("float32") - test_ds.read(1)
                min_ = diff.min()
                max_ = diff.max()
                n_pixels = (np.abs(diff) != 0).sum()
                msg = (
                    "Mismatch:\nRef: {}\nTest: {}\n"
                    "Min Difference: {}\n"
                    "Max Difference: {}\n"
                    "No. Pixels Different: {}\n"
                )
                print(msg.format(ref_fname, test_fname, min_, max_, n_pixels))


if __name__ == "__main__":
    description = "Compare the output image files."
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "--reference_dir",
        required=True,
        help="The filepath to the reference data directory.",
    )
    parser.add_argument(
        "--test_dir", required=True, help="The filepath to the test data directory."
    )
    parser.add_argument(
        "--files",
        required=True,
        help=("The pathname to a file containing a list" "of files to compare."),
    )
    parser.add_argument(
        "--scenes",
        required=True,
        help=("The pathname to a file containing a list" "of scenes to process."),
    )

    parsed_args = parser.parse_args()
    ref_dir = parsed_args.reference_dir
    test_dir = parsed_args.test_dir

    with open(parsed_args.files) as src:
        files = src.readlines()

    with open(parsed_args.scenes) as src:
        scenes = src.readlines()

    files = [f.strip() for f in files]
    scenes = [s.strip() for s in scenes]

    main(ref_dir, test_dir, scenes, files)
