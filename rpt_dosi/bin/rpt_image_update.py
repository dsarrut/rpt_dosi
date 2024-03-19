#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_image", "-i", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="output filename")
@click.option("--scaling", "-s", default=float(1), help="Scaling factor")
@click.option("--unit", "-u",
              default=None,
              help=f"Set the image unit {[k.authorized_units for k in rim.image_builders.values()]}"
              )
@click.option("--image_type", "-t",
              default=None,
              help=f"Set the type of image {[k for k in rim.image_builders.keys()]}"
              )
@click.option("--injected_activity", "--ia",
              default=None, type=float, help="Injected activity in MBq",
              )
@click.option("--body_weight", "--bw",
              default=None, type=float, help="Body weight in kg",
              )
# FIXME description
def go(input_image, unit, image_type, output,
       scaling, injected_activity, body_weight):
    # read image
    im = rim.read_image(input_image)

    if image_type is not None:
        im = rim.change_image_type(im, image_type)

    # set info
    if injected_activity is not None:
        im.injection_activity_mbq = injected_activity
    if body_weight is not None:
        im.body_weight_kg = body_weight

    # convert the unit
    if unit is not None:
        im.unit = unit

    # scaling
    im.image = im.image * scaling

    # write image and metadata
    im.write(output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
