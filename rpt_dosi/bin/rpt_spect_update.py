#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--spect", "-i", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="output filename")
@click.option("--convert", "-c",
              default=None,
              help=f"Convert the image unit {[k.authorized_units for k in rim.image_builders.values()]}"
              )
@click.option("--unit", "-u",
              default=None,
              help=f"If the image unit is not set, "
                   f"use this value ({[k.authorized_units for k in rim.image_builders.values()]})"
              )
@click.option("--scaling", "-s",
              default=1.0,
              help=f"Scale the pixel value"
              )
def go(spect, unit, output, convert, scaling):
    # read image
    spect = rim.read_spect(spect, unit=unit)

    # convert unit
    if convert is not None:
        spect.convert_to_unit(convert)

    # scale the value
    if scaling != 1:
        spect.image = spect.image * scaling

    # write image and metadata
    spect.write(output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
