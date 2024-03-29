import rpt_dosi.dicom_utils as di
import rpt_dosi.images as im
import shutil
import json
from box import Box
from datetime import datetime
import numpy as np
from .helpers import fatal


def db_update_injection(db, dicom_ds, cycle_id):
    # extract injection
    rad = di.dicom_read_injection(dicom_ds)

    # create cycle if not exist
    if cycle_id not in db["cycles"]:
        db["cycles"][cycle_id] = {}

    # update the db: cycle
    # FIXME maybe check already exist ?
    cycle = db["cycles"][cycle_id]
    cycle["injection"].update(rad)

    return db


def db_update_acquisition(db, dicom_ds, cycle_id, tp_id):
    # extract the date/time
    dt = di.dicom_read_acquisition_datetime(dicom_ds)

    cycle = db["cycles"][cycle_id]

    # create cycle if not exist
    if tp_id not in cycle["acquisitions"]:
        cycle["acquisitions"][tp_id] = {}

    # update the db: acquisition
    acqui = cycle["acquisitions"][tp_id]
    acqui.update(dt)

    return db


def db_update_cycle_rois_activity(cycle):
    # loop acquisitions
    for acq_id in cycle.acquisitions:
        print(f"Acquisition {acq_id}")
        acq = cycle.acquisitions[acq_id]
        if 'rois' not in acq:
            fatal(f"Acquisition {acq_id} has no rois")
        image_filename = acq.spect_image
        if "calibrated_spect_image" in acq:
            image_filename = acq.calibrated_spect_image
            print(f"Using calibrated spect image {image_filename}")
        s = im.get_stats_in_rois(image_filename, acq.ct_image, acq.rois)
        acq["activity"] = s


def db_load(filename):
    # open db as a dict
    f = open(filename, "r")
    db = Box(json.load(f))
    return db


def db_save(db, output, db_file=None):
    if output is None:
        output = db_file
        b = db_file.replace(".json", ".json.backup")
        shutil.copy(db_file, b)
    with open(output, "w") as f:
        json.dump(db, f, indent=2)


def db_get_time_interval(cycle, acquisition):
    idate = datetime.strptime(cycle.injection.datetime, "%Y-%m-%d %H:%M:%S")
    adate = datetime.strptime(acquisition.datetime, "%Y-%m-%d %H:%M:%S")
    hours_diff = (adate - idate).total_seconds() / 3600
    return hours_diff


def db_get_tac(cycle, roi_name):
    times = []
    activities = []
    for acq in cycle.acquisitions.values():
        if roi_name in acq.activity.keys():
            activities.append(acq.activity[roi_name].sum)
            d = db_get_time_interval(cycle, acq)
            times.append(d)
    return np.array(times), np.array(activities)
