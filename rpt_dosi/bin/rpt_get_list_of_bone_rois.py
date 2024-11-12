#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import fnmatch
import json
import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("folder", nargs=1, required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="output json filename")
def go(folder, output):
    # Path to the directory that contains the roi
    folder = Path(folder)

    pattern = [
        "clavicula",
        "femur",
        "hip_",
        "humerus",
        "rib_",
        "vertebrae",
        "sacrum",
        "scapula",
    ]

    files = find_files_containing_pattern(folder, pattern)

    roi_list = []
    for f in files:
        d = {"filename": os.path.basename(f)}
        roi_list.append(d)

    print(f"Find {len(roi_list)} files, save in {output}")
    with open(output, "w") as f:
        json.dump(roi_list, f, indent=4)


def find_files_containing_pattern(folder_path, keep_pattern):
    # List to hold the filenames containing the "pattern"
    pattern_files = []

    # List of file patterns to match
    file_patterns = ["*.nii", "*.nii.gz", "*.mhd"]

    for root, dirs, files in os.walk(folder_path):
        for pattern in file_patterns:
            for filename in fnmatch.filter(files, pattern):
                for p in keep_pattern:
                    if p in filename:
                        pattern_files.append(os.path.join(root, filename))

    return pattern_files


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
