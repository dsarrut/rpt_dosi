#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.dicom_utils as dicom
import json
from box import Box

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('dicomdir_json', type=click.Path(exists=True), nargs=1)
def go(dicomdir_json):
    # load the dicom info
    with open(dicomdir_json, "r") as f:
        studies = json.load(f)

    # sort series by date
    series = dicom.sort_series_by_date(studies)

    # get text for all series
    series_txt = []
    for s in series:
        t = dicom.print_series(s)
        ps = Box({"id": s.series_idx, "text": t})
        series_txt.append(ps)
        print(f'{ps.id} {ps.text}')


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
