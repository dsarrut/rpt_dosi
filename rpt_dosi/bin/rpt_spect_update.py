#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.images as rim
import SimpleITK as sitk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input_image", "-i", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="output filename")
@click.option("--calibration_factor", "-s", "-c", default=float(1), help="Scaling factor")
@click.option("--input_unit", "-u",
              type=click.Choice(rim.ImageSPECT.authorized_units),
              required=True,
              help=f"SPECT unit: {rim.ImageSPECT.authorized_units}")
@click.option("--output_unit",
              type=click.Choice(rim.ImageSPECT.authorized_units),
              default=None,
              help=f"Output SPECT unit {rim.ImageSPECT.authorized_units}")
@click.option("--injected_activity", "--ia",
              default=None, type=float, help="Injected activity in MBq",
              )
@click.option("--body_weight", "--bw",
              default=None, type=float, help="Body weight in kg",
              )
def go(input_image, input_unit, output_unit, output, calibration_factor, injected_activity, body_weight):
    spect = rim.read_spect(input_image, input_unit)
    print(f'Total Activity before : {spect.compute_total_activity():.1f} Bq')
    if output_unit is not None:
        if output_unit == "SUV":
            spect.body_weight_kg = body_weight
            spect.injection_activity_mbq = injected_activity
            spect.unit = "SUV"
        else:
            spect.unit = output_unit
    if calibration_factor != 1:
        spect.image = spect.image * calibration_factor
    print(f'Total Activity after  : {spect.compute_total_activity():.1f} Bq')
    sitk.WriteImage(spect.image, output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
