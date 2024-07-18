#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rdb
import rpt_dosi.dosimetry as dosi
import matplotlib.pyplot as plt
import numpy as np
import radioactivedecay as rd
import json

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--db_file", "--db", required=True, help="Input db.json")
@click.option("--cycle_id", "-c", required=True, help="Cycle to plot")
@click.option("--rad", default="Lu177", help="Radionuclide")
@click.option("--no_plot", is_flag=True, help="Plot the fit")
@click.option("--roi", '-r', multiple=True, help="Names of the roi image (nothing if all)")
@click.option(
    "--output", "-o", default=None, help="Save the fit parameters in this json file"
)
def go(db_file, cycle_id, rad, no_plot, output, roi):
    # open db as a dict
    db = rdb.PatientTreatmentDatabase(db_file)

    # get cycle
    cycle = db.get_cycle(cycle_id)

    # get all roi names with activity
    if len(roi) == 0:
        roi_names = set()
        for tp in cycle.timepoints.values():
            for roi in tp.rois.values():
                roi_names.add(roi.name)
    else:
        roi_names = set(roi)

    # decay
    isotope = rd.Nuclide(rad)
    half_life_h = isotope.half_life("h")
    print(f"Radionuclide half life {rad} = {half_life_h:.2f} h")
    decay_constant = np.log(2) / half_life_h

    # get tac and fit for all rois
    params = {}
    times, activities = rdb.compute_time_activity_curve(cycle, roi_names)
    for roi_name in roi_names:
        t = np.array(times[roi_name])
        a = np.array(activities[roi_name])
        a = dosi.decay_corrected_tac(t, a, decay_constant)
        r = dosi.triexpo_fit(t, a)
        r["rmse"] = dosi.triexpo_rmse(
            t, a, decay_constant, *dosi.triexpo_param_from_dict(r)
        )
        times[roi_name] = t
        activities[roi_name] = a
        params[roi_name] = r

    # store the fit in the db ?
    if output is not None:
        for r in params.keys():
            params[r]["times"] = list(times[r])
            params[r]["activities"] = list(activities[r])
        with open(output, "w") as f:
            json.dump(params, f, indent=2)

    # plot ?
    if no_plot:
        return

    # colors
    default_color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    # plot
    ic = 0
    for roi_name in roi_names:
        t = times[roi_name]
        r = params[roi_name]
        c = default_color_cycle[ic]
        # plot raw values (convert to MBq)
        plt.scatter(t, activities[roi_name] / 1e6, label=f"{roi_name}", color=c, s=30)
        # plot fitted values
        last_timepoint = t[-1] + 10  # add 10 hours
        x = np.linspace(0, last_timepoint, 100)
        # convert to MBq (/1e6)
        y = dosi.triexpo_apply_from_dict(x, decay_constant, r) / 1e6
        err = r["rmse"] / 1e6
        plt.plot(x, y, "--", label=f"fit {roi_name}, rmse={err:.3f}", color=c)
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
