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
@click.option("--sigma", default=None,
              help="specify sigma for gauss filter (None=no gauss, 0 = auto)",
              )
def go(input_image, spacing, output, sigma, like):
    # read image
    ct = rpt.read_ct(input_image)

    # resample
    if like is not None:
        im = rpt.ImageBase()
        im.read(like)
        ct = rpt.resample_ct_like(ct, im, sigma)
    else:
        ct = rpt.resample_ct_spacing(ct, spacing, sigma)

    # write
    ct.write(output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
