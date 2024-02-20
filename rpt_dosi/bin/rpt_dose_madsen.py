#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import click
from rpt_dosi import dosimetry as dosi
import SimpleITK as itk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--spect",
    "-s",
    required=True,
    type=click.Path(exists=True),
    help="Input SPECT image",
)
@click.option(
    "--ct",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Input CT image",
)
@click.option("--output", "-o", required=True, help="Output txt filename")
@click.option(
    "--roi",
    "-r",
    type=(str, str),
    multiple=True,
    help="ROI filename and name",
)
@click.option(
    "--roi_list", "-l", type=str, help="Filename : list of ROI filename and name"
)
@click.option("--acq_time", "-t", type=float, required=True, help="Time in h")
@click.option("--verbose", "-v", default=False, is_flag=True, help="Verbose")
def go(spect, ct, roi, acq_time, roi_list, verbose, output):
    # read both images
    spect = itk.ReadImage(spect)
    ct = itk.ReadImage(ct)
    # compute
    results = dosi.dose_madsen(spect, ct, roi, acq_time, roi_list, verbose)
    # save output to json
    with open(output, "w") as f:
        json.dump(results, f, indent=4)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
