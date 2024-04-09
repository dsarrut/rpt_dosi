#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rdb
import rpt_dosi.images as rim
import SimpleITK as itk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--db_file", "--db", required=True, help="Input db.json")
@click.option(
    "--output", "-o", default=None, help="Output json (same as input if None)"
)
@click.option(
    "--calibration_factor",
    "-c",
    required=True,
    type=float,
    help="SPECT calibration factor",
)
def go(db_file, output, calibration_factor):
    # FIXME : the way the db is managed will be changed with classes instead of dic

    # open db as a dict
    db = rdb.db_load(db_file)

    # loop on cycles
    for cycle_id in db.cycles:
        print(f"Cycle {cycle_id}")
        cycle = db.cycles[cycle_id]
        # loop acquisitions
        for acq_id in cycle.acquisitions:
            print(f"Acquisition {acq_id}")
            acq = cycle.acquisitions[acq_id]
            input_image = acq.spect_image
            print(f"Input image: {input_image}")
            # read image
            spect = rim.read_spect(input_image)
            spect.require_unit('Bq')
            print(spect)
            # apply calibration
            spect.image = spect.image * calibration_factor
            # write
            output_image = input_image.replace(".nii.gz", "_calibrated.nii.gz")
            itk.WriteImage(spect.image, output_image)
            acq.calibrated_spect_image = output_image
            print(f"Calibrated spect image: {acq.calibrated_spect_image}")

    # save
    rdb.db_save(db, output, db_file)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
