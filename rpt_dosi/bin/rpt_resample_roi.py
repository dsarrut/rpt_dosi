#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rpt
import SimpleITK as sitk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_image", "-i", required=True, type=click.Path(exists=True))
@click.option("--spacing", "-s", default=4.0, help="isotropic spacing in mm")
@click.option(
    "--like",
    "-l",
    default=None,
    type=str,
    help="Resample like another image (spacing is ignored)",
)
@click.option("--output", "-o", required=True, help="output filename")
def go(input_image, spacing, output, like):
    # read image
    roi = sitk.ReadImage(input_image)

    # resample
    if like is not None:
        like = sitk.ReadImage(like)
        roi = rpt.resample_image_like(roi, like, default_pixel_value=0, linear=False)
    else:
        roi = rpt.resample_image(roi, spacing, default_pixel_value=0, linear=False)

    # write
    sitk.WriteImage(roi, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
