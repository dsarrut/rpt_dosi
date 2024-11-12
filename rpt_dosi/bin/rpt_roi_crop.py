#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import itk
import gatetools as gt
from pathlib import Path
import os
import rpt_dosi.utils as ru

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("input_images", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--output_folder", "-o", required=True, help="output folder")
def go(input_images, output_folder):
    output_folder = Path(output_folder)
    os.makedirs(output_folder, exist_ok=True)

    all_filenames = []
    extensions = [".mhd", ".nii.gz"]
    for filename in input_images:
        if os.path.isdir(filename):
            for root, dirs, files in os.walk(filename):
                for f in files:
                    fn, ext = ru.get_basename_and_extension(f)
                    if ext in extensions:
                        all_filenames.append(os.path.join(root, f))
        else:
            all_filenames.append(filename)

    print(f"Processing {len(all_filenames)} files")
    for filename in all_filenames:
        print(f"Cropping {filename} ...")
        img = itk.imread(filename)
        o = gt.image_auto_crop(img, bg=0)
        fn, ext = ru.get_basename_and_extension(filename)
        fn = f"{fn}_crop{ext}"
        print(f"Saving in {fn}")
        itk.imwrite(o, output_folder / fn)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
