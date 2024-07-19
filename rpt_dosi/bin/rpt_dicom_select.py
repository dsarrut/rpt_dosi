#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.dicom_utils as rdicom
import json

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--dicom_dir", "-i", required=True, help="Input DICOM DIR json")
@click.option("--output", "-o", required=True, help="Output json file with selected dicom")
def go(dicom_dir, output):
    # get the series
    with open(dicom_dir, "r") as f:
        studies = json.load(f)
    series = rdicom.sort_series_by_date(studies)

    # add the input columns
    for s in series:
        s['cycle_id'] = ""
        s['tp_id'] = ""
        s['name'] = ""

    # start GUI
    app = rdicom.DicomSelectionGUI(series, output)
    app.mainloop()


if __name__ == "__main__":
    go()
