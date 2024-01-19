import json
import click
import glob
import gatetools as gt
import SimpleITK as sitk
import os
import shutil
from datetime import datetime
import rpt_dosi.images as rim
import rpt_dosi.dosimetry as rd

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--patient", "-p", help="Patient name", required=True, type=str)
def click_computedose(patient):
    computedose(patient)


def computedose(patient):
    # read the json
    f = open(patient + '.json')
    data = json.load(f)
    outputResults = {}
    outputResults["cycle"] = {}

    # compute dose for all ct images
    for cycle in data["cycle"].keys():
        outputResults["cycle"][cycle] = {}
        for acquisition in data["cycle"][cycle]["acquisition"]:
            outputResults["cycle"][cycle][acquisition["label"]] = []
            path = patient + "/cycle_" + cycle + "/" + acquisition["label"]
            ct = sitk.ReadImage(path + "/ct.nii")
            spect = sitk.ReadImage(path + "/spect.nii")
            ct_resampled = rim.resample_image_like(ct, spect, default_pixel_value=-1000.0)
            spect_calibrated = rd.spect_calibration(spect, 0.176906614, False, verbose=True)

            #create oar.json
            dataJSON = []
            dataJSON.append({
               "roi_name": "liver",
               "roi_filename": patient + "/cycle_" + cycle + "/" + acquisition["label"] + "/rois/liver.nii.gz"
                })
            dataJSON.append({
               "roi_name": "spleen",
               "roi_filename": patient + "/cycle_" + cycle + "/" + acquisition["label"] + "/rois/spleen.nii.gz"
                })
            dataJSON.append({
               "roi_name": "left kidney",
               "roi_filename": patient + "/cycle_" + cycle + "/" + acquisition["label"] + "/rois/kidney_left.nii.gz"
                })
            dataJSON.append({
               "roi_name": "right kidney",
               "roi_filename": patient + "/cycle_" + cycle + "/" + acquisition["label"] + "/rois/kidney_right.nii.gz"
                })
            with open("oar.json", "w") as outfile:
                json.dump(dataJSON, outfile, indent=4)

            #compute acquisition time
            acq_time = datetime.strptime(acquisition["date"], "%d/%m/%Y, %H:%M:%S") - datetime.strptime(data["cycle"][cycle]["injection"]["injection_datetime"], "%d/%m/%Y, %H:%M:%S")
            acq_time = acq_time.total_seconds()/3600.0
            results = rd.rpt_dose_hanscheid(spect_calibrated, ct_resampled, (), acq_time, "oar.json", False, phantom="ICRP 110 AM", rad="Lu177", method="2017")
            outputResults["cycle"][cycle][acquisition["label"]].append(results)
            results = rd.rpt_dose_hanscheid(spect_calibrated, ct_resampled, (), acq_time, "oar.json", False, phantom="ICRP 110 AM", rad="Lu177", method="2018")
            outputResults["cycle"][cycle][acquisition["label"]].append(results)

    # print ok
    with open(patient + "_results.json", "w") as outfile:
        json.dump(outputResults, outfile, indent=4)
    print("Dose computed, results are in " + patient + "_results.json")

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    click_computedose()
