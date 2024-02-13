#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rptdb
import json
from box import BoxList
from pathlib import Path
import copy

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--db_file", "--db", required=True, help="Input db.json")
@click.option(
    "--output", "-o", default=None, help="Output json (same as input if None)"
)
@click.option(
    "--roi_list", "-l", type=str, help="Filename json : list of ROI filename and name"
)
@click.option("--name", "-n", required=True, help="Patient initials (folder)")
def go(db_file, roi_list, name, output):
    # open db as a dict
    db = rptdb.db_load(db_file)

    # consider list of roi/name
    with open(roi_list, "r") as f:
        rois = BoxList(json.load(f))

    # loop on cycles
    for cycle_id in db.cycles:
        print(f"Cycle {cycle_id}")
        cycle = db.cycles[cycle_id]
        for acquisition in cycle.acquisitions:
            print(f"Acquisition {acquisition}")
            rois_copy = copy.copy(rois)
            for roi in rois_copy:
                roi.roi_filename = str(Path(name) / cycle_id / acquisition / roi.roi_filename)
            cycle.acquisitions[acquisition]["rois"] = rois_copy

    # save
    rptdb.db_save(db, output, db_file)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
