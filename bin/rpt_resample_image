#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rpt
import SimpleITK as itk

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
@click.option("--def_pixel", "-d", default=-1000.0, help="default pixel value")
@click.option(
    "--no_gauss",
    "--ng",
    is_flag=True,
    help="Do not apply gauss filter before subsampling",
)
@click.option(
    "--sigma",
    default=0,
    help="specify sigma for gauss filter (if 0 = auto)",
)
def go(input_image, spacing, output, no_gauss, sigma, like, def_pixel):
    # read image
    ct = itk.ReadImage(input_image)

    # gauss ?
    if not no_gauss:
        if sigma <= 0:
            sigma = [0.5 * sp for sp in ct.GetSpacing()]
        ct = rpt.apply_gauss_smoothing(ct, sigma)

    # resample
    if like is not None:
        like = itk.ReadImage(like)
        ct = rpt.resample_image_like(ct, like, default_pixel_value=def_pixel)
    else:
        ct = rpt.resample_image(ct, spacing, default_pixel_value=def_pixel)

    # write
    itk.WriteImage(ct, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
