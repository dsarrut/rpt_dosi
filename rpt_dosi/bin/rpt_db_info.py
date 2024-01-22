#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rptdb
from datetime import datetime

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--db_file", "--db", required=True, help="Input db.json")
def go(db_file):
    # open db as a dict
    db = rptdb.db_load(db_file)

    # loop on cycles
    if len(db.cycles) > 1:
        print(f"There are {len(db.cycles)} cycles")
    else:
        print(f"There is {len(db.cycles)} cycle")
    for cycle_id, cycle in db.cycles.items():
        if "injection" in cycle:
            idate = datetime.strptime(cycle.injection.datetime, "%Y-%m-%d %H:%M:%S")
        else:
            idate = "unknown"
        print(f'Cycle "{cycle_id}" injection time: {idate}')
        for acq_id in cycle.acquisitions:
            acq = cycle.acquisitions[acq_id]
            try:
                adate = datetime.strptime(acq.datetime, "%Y-%m-%d %H:%M:%S")
                hours_diff = (adate - idate).total_seconds() / 3600
                print(f"Acquisition {acq_id} : {hours_diff:.3f} hours")
            except:
                print(f"Acquisition {acq_id} : unknown datetime")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
