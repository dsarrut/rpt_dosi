#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_image", "-i", required=True, type=click.Path(exists=True))
def go(input_image):
    # read image
    im = rim.ImageBase()
    im.filename = input_image
    im.read_metadata()
    im.read_header()
    print(im.info())


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
