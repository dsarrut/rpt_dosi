#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rpt
import SimpleITK as sitk
import numpy as np

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
@click.option("--def_pixel", "-d", default=0.0, help="default pixel value")
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
@click.option("--bq",
              is_flag=True,
              default=False,
              help="Set this flag if the spect is in Bq to ")
def go(input_image, spacing, output, no_gauss, sigma, like, def_pixel, bq):
    # read image
    spect = sitk.ReadImage(input_image)

    # initial voxel volume
    volume_voxel_mL = np.prod(spect.GetSpacing()) / 1000

    # gauss ?
    if not no_gauss:
        if sigma <= 0:
            sigma = [0.5 * sp for sp in spect.GetSpacing()]
        spect = rpt.apply_gauss_smoothing(spect, sigma)

    # resample
    if like is not None:
        like = sitk.ReadImage(like)
        spect = rpt.resample_image_like(spect, like, default_pixel_value=def_pixel)
    else:
        spect = rpt.resample_image(spect, spacing, default_pixel_value=def_pixel)

    # adjust Bq ?
    if bq:
        final_volume_voxel_mL = np.prod(spect.GetSpacing()) / 1000
        s = final_volume_voxel_mL / volume_voxel_mL
        a = sitk.GetArrayViewFromImage(spect)
        a = a*s
        s = sitk.GetImageFromArray(a)
        s.CopyInformation(spect)
        spect = s

    # write
    sitk.WriteImage(spect, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
