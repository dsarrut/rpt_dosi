#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import pydicom
import rpt_dosi.db as rptdb

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--db_file", "--db", required=True, help="Input db.json")
@click.option(
    "--output", "-o", default=None, help="Output json (same as input if None)"
)

def go(db_file, output):
    # open db as a dict
    db = rptdb.db_load(db_file)

    # loop on cycle
    for cycle_id, cycle in db["cycles"].items():
        for tp_id, acqui in cycle["acquisitions"].items():
            # open dicom as a dataset
            dicom_file = acqui["spect_dicom"]
            ds = pydicom.read_file(dicom_file)
            # update acquisition
            db = rptdb.db_update_acquisition(db, ds, cycle_id, tp_id)
            print(f'Cycle {cycle_id}, {tp_id} : {acqui["datetime"]}')

    # save
    rptdb.db_save(db, output, db_file)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
