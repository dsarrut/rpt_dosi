#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim
import SimpleITK as itk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--input_image",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Input image",
)
@click.option("--output", "-o", required=True, help="output filename")
@click.option("--roi", "-r", default="rois/body.nii.gz", help="body ROI filename")
@click.option(
    "--bg_value",
    default=-1000,
    help="Lower threshold: all pixels "
    "values strictly below will be considered as background",
)
def go(input_image, roi, output, bg_value):
    # read images
    img = itk.ReadImage(input_image)
    roi = itk.ReadImage(roi)

    # check images spacing
    if not rim.images_have_same_domain(img, roi):
        roi = rim.resample_itk_image_like(roi, img, default_pixel_value=0, linear=False)

    # set background
    img = rim.image_set_background(img, roi, bg_value=bg_value, roi_bg_value=0)

    # crop
    img = rim.crop_to_bounding_box(img, lover_threshold=bg_value)

    # write
    itk.WriteImage(img, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
