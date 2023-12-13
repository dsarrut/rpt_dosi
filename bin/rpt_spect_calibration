#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.dosimetry as rd
import SimpleITK as itk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_image", "-i", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="output filename")
@click.option(
    "--calibration_factor",
    "-c",
    required=True,
    type=float,
    help="SPECT calibration factor",
)
@click.option(
    "--concentration",
    is_flag=True,
    default=False,
    help="use concentration instead of Bqml",
)
def go(input_image, output, calibration_factor, concentration):
    # read image
    img = itk.ReadImage(input_image)
    # apply calibration
    img = rd.spect_calibration(img, calibration_factor, concentration, verbose=True)
    # write
    itk.WriteImage(img, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
