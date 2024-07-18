#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rdb
import matplotlib.pyplot as plt

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--db_file", "--db", required=True, help="Input db.json")
@click.option("--cycle_id", "-c", required=True, help="Cycle to plot")
@click.option("--spect_name", default='spect', help="Name of the spect image")
@click.option("--roi", '-r', multiple=True, help="Names of the roi image (nothing if all)")
# resample ?
def go(db_file, cycle_id, spect_name, roi):
    db = rdb.PatientTreatmentDatabase(db_file)
    cycle = db.get_cycle(cycle_id)

    # get all roi names with activity
    if len(roi) == 0:
        roi_names = set()
        for tp in cycle.timepoints.values():
            for roi in tp.rois.values():
                roi_names.add(roi.name)
    else:
        roi_names = set(roi)

    # go
    times, activities = rdb.compute_time_activity_curve(cycle, roi_names, spect_name)

    # plot
    for roi in roi_names:
        t = times[roi]
        a = activities[roi]
        plt.plot(t, a, '-o', label=f"{roi}")

    plt.xlabel("Time in hours")
    plt.ylabel("Activity in MBq")
    plt.title("Time-Activity Curve")
    plt.grid(True)
    plt.legend()
    plt.show()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
