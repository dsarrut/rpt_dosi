#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.dicom_utils as dicom
import rpt_dosi.utils as he
import json
import os

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--dicom_folder", "-i", required=True, help="Input DICOM folder")
@click.option("--output", "-o", required=True, help="Output json file with dicom info")
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Loop in the folder and browse dicom in all sub-folders (first depth only)",
)
def go(dicom_folder, output, recursive):
    if recursive:
        folders = he.get_subfolders(dicom_folder, depth=0)
        if os.path.dirname(output):
            he.fatal(
                f"With the option -r, output must be a simple filename without folders"
            )
    else:
        folders = [dicom_folder]

    print(f"Processing folders: {folders}")
    for folder in folders:
        print(f"Processing {folder} ... ")

        # analyse the folder for dicom
        studies = dicom.list_dicom_studies_and_series(folder)

        # store as a json file
        if recursive:
            output_filename = os.path.join(folder, output)
        else:
            output_filename = output
        with open(output_filename, "w") as f:
            json.dump(studies, f, indent=2)
        print(output_filename)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
