import json
import click
import syd2json
import glob
import gatetools as gt
import itk
import os
import shutil

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--db", "-db", help="Input database", required=True, type=click.Path(dir_okay=False)
)
@click.option("--patient", "-p", help="Patient name", required=True, type=str)
def click_syd2totalSegmentator(db, patient):
    syd2totalSegmentator(db, patient)


def syd2totalSegmentator(db, patient):
    syd2json.extract_patient(db, patient)

    # read the json
    f = open(patient + '.json')
    data = json.load(f)

    # convert to nii all ct images
    for cycle in data["cycle"].keys():
        for acquisition in data["cycle"][cycle]["acquisition"]:
            path = patient + "/cycle_" + cycle + "/" + acquisition["label"]
            os.makedirs(path, exist_ok=True)
            os.makedirs(path + "/rois", exist_ok=True)
            for modality in ["ct", "spect"]:
                print("Convert " + acquisition[modality])
                os.makedirs(path + "/" + modality, exist_ok=True)
                files = glob.glob(acquisition[modality] + "/**/*.dcm", recursive=True)
                for file in files:
                    shutil.copy(file, path + "/" + modality + "/" + os.path.basename(file))
                if len(files) > 1:
                    image = gt.read_dicom(files)
                else:
                    image = gt.read_3d_dicom(files)
                itk.imwrite(image, path + "/" + modality + ".nii")

    # print transfert for Total Segmentator
    print("Folder is ready to be segmented with total segmentator")

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    click_syd2totalSegmentator()
