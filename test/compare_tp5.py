#!/usr/bin/env python

import argparse
from os.path import exists
from os.path import join as pjoin


def main(ref_dir, test_dir, scenes, files):
    for scene in scenes:
        ref_scene = pjoin(ref_dir, scene)
        test_scene = pjoin(test_dir, scene)
        for f in files:
            ref_fname = pjoin(pjoin(ref_scene, "mod"), f)
            test_fname = pjoin(pjoin(test_scene, "mod"), f)
            if not exists(ref_fname):
                continue
            print(f"Testing\nScene: {scene}\n File: {f}")
            with open(ref_fname) as ref, open(test_fname) as test:
                ref_data = ref.readlines()
                test_data = test.readlines()
                for i in range(len(ref_data)):
                    if not ref_data[i] == test_data[i]:
                        print(f"Line {i} not equivilent")


if __name__ == "__main__":
    description = "Compare the output tp5 files."
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
