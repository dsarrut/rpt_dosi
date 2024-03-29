#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rptdb
import matplotlib.pyplot as plt

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--db_file", "--db", required=True, help="Input db.json")
@click.option("--cycle_id", "-c", required=True, help="Cycle to plot")
def go(db_file, cycle_id):
    # open db as a dict
    db = rptdb.db_load(db_file)

    # get cycle
    cycle = db.cycles[cycle_id]

    # get all roi names with activity
    roi_names = set()
    for acq in cycle.acquisitions.values():
        for r in acq.activity.keys():
            roi_names.add(r)
    print(f"Plotting {len(roi_names)} ROIs")

    # get tac for all rois
    for roi in roi_names:
        t, a = rptdb.db_get_tac(cycle, roi)
        a = a / 1e6
        # a = a / injected_activity * 100
        plt.plot(t, a, label=f"{roi}")

    plt.xlabel("Time in hours")
    plt.ylabel("Activity in MBq")
    # plt.ylabel('% IA')
    plt.title("Time-Activity Curve")
    plt.grid(True)
    plt.legend()
    plt.show()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
