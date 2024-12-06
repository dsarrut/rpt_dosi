#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import copy

import click
import SimpleITK as sitk
import rpt_dosi.utils as ru
import rpt_dosi.images as rim

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("input_images", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="output filename")
@click.option("--crop", "-c", default=True, help="Crop final combined image")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose")
@click.option(
    "--operator", "-op", default="or", help="Boolean operator: or and xor and not"
)
def go(input_images, output, operator, crop, verbose):

    if len(input_images) < 2:
        ru.fatal(f"At least 2 images must be provided")

    verbose and print(input_images[0])
    mimg1 = rim.read_roi(input_images[0])
    img1 = mimg1.image
    for mask_filename in input_images[1:]:
        verbose and print(f"{mask_filename}, current size is {img1.GetSize()}")
        mimg2 = rim.read_roi(mask_filename)
        img1 = rim.roi_boolean_operation(img1, mimg2.image, operator)

    # final crop
    if crop:
        img1 = rim.crop_to_bounding_box(img1, bg_value=0)
    verbose and print(f"Final size is {img1.GetSize()}")
    sitk.WriteImage(img1, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
