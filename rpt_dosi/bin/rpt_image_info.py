#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('input_images', type=click.Path(exists=True), nargs=-1)
def go(input_images):
    for input_image in input_images:
        # read image
        im = rim.read_metaimage(input_image, reading_mode="header_only")
        print(im.info())


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
