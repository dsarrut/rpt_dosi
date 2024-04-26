#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim

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
@click.option("--output", "-o", default=None, help="Output json filename")
def go(input_image, ct, roi, output):
    # read spect
    spect = rim.read_spect(input_image)

    # read roi
    roi = rim.read_roi(roi, "unnamed_roi")
    roi = rim.resample_roi_like(roi, spect)

    # get stats
    res = rim.image_roi_stats(roi, spect, "spect")
    if ct is not None:
        ct = rim.read_ct(ct)
        ct = rim.resample_ct_like(ct, spect)
        densities = ct.compute_densities()
        roi.update_mass_and_volume(densities)
        res["mass_g"] = roi.mass_g

    print(res)
    if output is not None:
        with open(output, "w") as f:
            json.dump(res, f, indent=4)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
