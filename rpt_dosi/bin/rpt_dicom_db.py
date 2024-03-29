#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rptdb
import rpt_dosi.helpers as he
import json
import os
from pathlib import Path

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--selected_json", "-i", required=True, help="Input DICOM selected json")
@click.option(
    "--run", "-r", is_flag=True, default=False, help="Run the convert commands"
)
@click.option("--output", "-o", required=True, help="Output folder")
def go(selected_json, run, output):
    # load the dicom info
    db = rptdb.db_load(selected_json)

    # output folder
    output = Path(output)
    os.makedirs(output, exist_ok=True)

    # loop on cycles
    cycles = db.cycles
    for cycle_id, cycle in cycles.items():
        os.makedirs(output / cycle_id, exist_ok=True)
        for tp_id, tp in cycle.acquisitions.items():
            f = output / cycle_id / tp_id
            os.makedirs(f, exist_ok=True)
            tp.ct_image = f"{f}/ct.nii.gz"
            tp.spect_image = f"{f}/spect.nii.gz"
            cmd = f"gt_image_convert {tp.ct_dicom}/*dcm -o {tp.ct_image}"
            cmd = he.escape_special_characters(cmd)
            print(cmd)
            if run:
                os.system(f"{cmd}")
            cmd = f"gt_image_convert {tp.spect_dicom} -o {tp.spect_image}"
            cmd = he.escape_special_characters(cmd)
            print(cmd)
            if run:
                os.system(f"{cmd}")

    # save the db
    o = output / "db.json"
    with open(o, "w") as outfile:
        json.dump(db, outfile, indent=2)
    print(o)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
