#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import click
from rpt_dosi import dosimetry as rd
import SimpleITK as sitk
from box import Box

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
@click.option("--output", "-o", required=True, help="Output json filename")
@click.option(
    "--roi_list", "-l", type=str, help="Filename : list of ROI filename and name"
)
@click.option("--acq_time", "-t", type=float, required=True, help="Time in h")
@click.option(
    "--phantom", "-p", default="ICRP 110 AM", help="Phantom ICRP 110 AF or AM"
)
@click.option("--rad", default="Lu177", help="Radionuclide")
@click.option("--verbose", "-v", default=False, is_flag=True, help="Verbose")
@click.option(
    "--method",
    "-m",
    default="hanscheid2018",
    type=click.Choice(["hanscheid2017", "hanscheid2018", "madsen2018"]),
    help="Which method to use",
)
def go(spect, ct, acq_time, phantom, rad, roi_list, verbose, output, method):
    # Reading images as itk image
    spect = sitk.ReadImage(spect)
    ct = sitk.ReadImage(ct)

    # Consider the list of roi/name,
    # this is a dict struct with roi_filename & roi_name
    with open(roi_list, "r") as f:
        rois = json.load(f)

    # options
    options = {
        "radionuclide": rad,
        "phantom": phantom,
        "verbose": verbose
    }

    # compute dose for all roi
    results = rd.dose_for_each_rois(spect, ct, rois, acq_time, method, options)

    # print
    for roi in rois:
        rn = roi['roi_name']
        res = Box(results[rn])
        print(f"{rn:<15}  {res.dose_Gy:.2f} Gy  {res.mass_g:.2f} g  {res.volume_ml:.2f} g mL")

    # save output to json
    with open(output, "w") as f:
        json.dump(results, f, indent=4)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
