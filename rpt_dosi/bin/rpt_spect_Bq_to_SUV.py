#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.dosimetry as rd
import SimpleITK as sitk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_image", "-i", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="output filename")
@click.option(
    "--injected_activity",
    "--ia",
    default=7400,
    type=float,
    help="Injected activity in MBq",
)
@click.option(
    "--body_weight", "--bw",
    default=75,
    help="Body weight in kg",
)
def go(input_image, output, injected_activity, body_weight):
    # read image
    img = sitk.ReadImage(input_image)
    # apply calibration
    img = rd.spect_Bq_to_SUV(img, injected_activity, body_weight)
    # write
    sitk.WriteImage(img, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
