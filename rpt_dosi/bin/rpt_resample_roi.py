#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rpt

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_image", "-i", required=True, type=click.Path(exists=True))
@click.option("--spacing", "-s", type=float, multiple=True,
              callback=rpt.validate_spacing,
              default=(4.0, 4.0, 4.0),
              show_default=True, help="Spacing in mm (one or three values)")
@click.option("--like", "-l", default=None, type=str,
              help="Resample like another image (spacing is ignored)",
              )
@click.option("--output", "-o", required=True, help="output filename")
def go(input_image, spacing, output, like):
    # read image
    roi = rpt.read_roi(input_image, "unknown_roi")

    # resample
    if like is not None:
        im = rpt.MetaImageBase()
        im.read(like)
        roi = rpt.resample_roi_like(roi, im)
    else:
        roi = rpt.resample_roi_spacing(roi, spacing)

    # write
    roi.write(output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
