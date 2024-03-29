#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rptdb
import rpt_dosi.dosimetry as dosi
import matplotlib.pyplot as plt
import numpy as np
import radioactivedecay as rd

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--db_file", "--db", required=True, help="Input db.json")
@click.option("--cycle_id", "-c", required=True, help="Cycle to plot")
@click.option("--rad", default="Lu177", help="Radionuclide")
@click.option("--no_plot", is_flag=True, help="Plot the fit")
@click.option(
    "--output", "-o", default=None, help="Save the fit parameters in this json db file"
)
def go(db_file, cycle_id, rad, no_plot, output):
    # open db as a dict
    db = rptdb.db_load(db_file)

    # get cycle
    cycle = db.cycles[cycle_id]

    # get all roi names with activity
    roi_names = set()
    for acq in cycle.acquisitions.values():
        for r in acq.activity.keys():
            roi_names.add(r)

    # decay
    isotope = rd.Nuclide(rad)
    half_life_h = isotope.half_life("h")
    print(f"Radionuclide half life {rad} = {half_life_h:.2f} h")
    decay_constant = np.log(2) / half_life_h

    # get tac and fit for all rois
    times = {}
    activities = {}
    params = {}
    for roi in roi_names:
        t, a = rptdb.db_get_tac(cycle, roi)
        a = dosi.decay_corrected_tac(t, a, decay_constant)
        r = dosi.triexpo_fit(t, a)
        r["rmse"] = dosi.triexpo_rmse(
            t, a, decay_constant, *dosi.triexpo_param_from_dict(r)
        )
        times[roi] = t
        activities[roi] = a
        params[roi] = r

    # store the fit in the db ?
    if output is not None:
        if "tri_expo_fit" not in cycle:
            cycle["tri_expo_fit"] = {}
        tef = cycle["tri_expo_fit"]
        for roi in roi_names:
            tef[roi] = params[roi]
        rptdb.db_save(db, output)

    # plot ?
    if no_plot:
        return

    # colors
    default_color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    # plot
    ic = 0
    for roi in roi_names:
        t = times[roi]
        r = params[roi]
        c = default_color_cycle[ic]
        # plot raw values (convert to MBq)
        plt.scatter(t, activities[roi] / 1e6, label=f"{roi}", color=c, s=30)
        # plot fitted values
        last_timepoint = t[-1] + 10  # add 10 hours
        x = np.linspace(0, last_timepoint, 100)
        # convert to MBq (/1e6)
        y = dosi.triexpo_apply_from_dict(x, decay_constant, r) / 1e6
        err = r["rmse"] / 1e6
        plt.plot(x, y, "--", label=f"fit {roi}, rmse={err:.3f}", color=c)
        ic = ic + 1

    plt.xlabel("Time in hours")
    plt.ylabel("Activity in MBq")
    plt.title("Time-Activity Curve fitted by tri exponential model")
    plt.grid(True)
    plt.legend()
    plt.show()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
