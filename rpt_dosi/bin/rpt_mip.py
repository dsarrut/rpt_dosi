#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as im
import SimpleITK as sitk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_filename", "-i",
              required=True,
              type=click.Path(exists=True),
              help="Input image",
              )
@click.option(
    "--output", "-o", required=True, help="Output filename",
)
@click.option(
    "--dim3", "-d", is_flag=True, default=False, help="2D or 3D",
)
def go(input_filename, dim3, output):
    # read image
    img = sitk.ReadImage(input_filename)
    # compute mip
    img = im.mip(img, dim3)
    # write
    sitk.WriteImage(img, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
