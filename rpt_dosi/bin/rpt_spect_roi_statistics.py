#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim
import json

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--input_image",
    "-s",
    required=True,
    type=click.Path(exists=True),
    help="Input SPECT image (use --unit to specify the image)",
)
@click.option(
    "--ct",
    "-c",
    default=None,
    type=click.Path(exists=True),
    help="Input CT image (optional, only for mass)",
)
@click.option(
    "--roi",
    "-r",
    required=True,
    type=click.Path(exists=True),
    help="Input ROI mask",
)
@click.option("--like", "-l", default="spect", type=str,
              help="Resample like: spect, roi or ct",
              )
@click.option("--unit", "-u",
              default="Bq/mL",
              help=f"Set the image unit {[k.authorized_units for k in rim.image_builders.values()]}"
              )
@click.option("--output", "-o", default=None, help="Output json filename")
def go(input_image, ct, roi, like, unit, output):
    # read spect
    spect = rim.read_spect(input_image, unit)

    # read roi
    roi = rim.read_roi(roi, "unnamed_roi")

    # read ct
    if ct is not None:
        ct = rim.read_ct(ct)

    # get stats
    res = rim.image_roi_stats(roi, spect, ct, like)

    # print and save
    print(res)
    if output is not None:
        with open(output, "w") as f:
            json.dump(res, f, indent=4)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
