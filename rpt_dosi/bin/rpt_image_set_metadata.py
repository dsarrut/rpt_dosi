#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim
from rpt_dosi.utils import fatal

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_image", "-i", required=True, type=click.Path(exists=True))
@click.option("--unit", "-u",
              default=None,
              help=f"Set the image unit {[k.authorized_units for k in rim.image_builders.values()]}"
              )
@click.option("--image_type", "-t",
              default=None,
              help=f"Set the type of image {[k for k in rim.image_builders.keys()]}"
              )
@click.option("--tag", type=(str, str), multiple=True, help="Add a tag key and value")
@click.option("--verbose", "-v", is_flag=True, help="verbose")
@click.option("--force", "-f", is_flag=True, help="If set to True, erase all previous metadata associated")
def go(input_image, unit, image_type, tag, verbose, force):
    # delete metadata before ?
    if force:
        rim.delete_image_metadata(input_image)

    # read the image header and associated metadata
    if rim.metadata_exists(input_image):
        im = rim.read_metaimage(input_image, read_header_only=True)
    else:
        if image_type is None:
            fatal('No image type specified, and no metadata found.')
        arg = {'unit': unit}
        for t in tag:
            arg[t[0]] = t[1]
        im = rim.new_metaimage(image_type, input_image, read_header_only=True, **arg)
        im.write_metadata()

    # convert the unit
    if unit is not None:
        # the image must be loaded to convert unit
        im.read()
        im.convert_to_unit(unit)
        # write the modified image
        im.write()

    # set tags values
    for t in tag:
        key, value = t[0], t[1]
        im.set_metadata(key, value)

    # verbose
    if verbose:
        print(im.info())

    # write metadata only
    im.write_metadata()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
