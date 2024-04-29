#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim

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
        rim.delete_metadata(input_image)

    # read image
    im = rim.read_image_header_only(input_image)
    if verbose:
        print('Input metadata')
        print(im.info())

    # set image type
    if image_type is not None:
        if image_type not in rim.image_builders.keys():
            rim.fatal(f"Unknown image type {image_type}. Available types are {rim.image_builders.keys()}")
        im = rim.build_image_from_type(image_type)
        im.filename = input_image
        im.write_metadata()
        im = rim.read_image_header_only(input_image)

    # convert the unit
    if unit is not None:
        im.unit = unit

    # set tags values
    for t in tag:
        key, value = t[0], t[1]
        im.set_tag(key, value)

    # verbose
    if verbose:
        print()
        print('Output metadata')
        print(im.info())

    # write metadata only
    im.write_metadata()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
