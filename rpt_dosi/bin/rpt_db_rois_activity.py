#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
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

    # loop on cycles
    for cycle_id in db.cycles:
        print(f"Cycle {cycle_id}")
        cycle = db.cycles[cycle_id]
        rptdb.db_update_cycle_rois_activity(cycle)

    # save
    rptdb.db_save(db, output, db_file)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
