import rpt_dosi.dicom_utils as rdicom
import rpt_dosi.images as rim
import shutil
import json
from box import Box
from datetime import datetime
import numpy as np
from .helpers import fatal
import os
from pathlib import Path


def db_update_injection(db, dicom_ds, cycle_id):
    # extract injection
    rad = rdicom.dicom_read_injection(dicom_ds)

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
    dt = rdicom.dicom_read_acquisition_datetime(dicom_ds)

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
        s = rim.get_stats_in_rois(image_filename, acq.ct_image, acq.rois)
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


class PatientTreatment:
    """
    Store information about a patient treatment:
    - all cycles, all imaging timepoints
    - consider a hierarchy folders patient/cycle_id/timepoint_id/images
    - from / to json files
    - when store to a json file, the database folder MUST be the one of the json file

    patient/
            db.json
            cycle1/
                   tp1/
                        ct.nii.gz
                        spect.nii.gz
                   tp2/ ...
            cycle2/ ...

    """

    def __init__(self, filename, create=False):
        self.patient_id = None
        self.body_weight_kg = None
        self.cycles = {}
        self._db_folder = None
        self.json_path = filename
        if os.path.exists(filename):
            self.read(filename)
        else:
            if create:
                self.write(filename)
            else:
                fatal(f'The database file {filename} does not exist')

    def info(self):
        s = (f'Patient id = {self.patient_id}\n'
             f'Data folder = {self.db_folder}\n'
             f'Body weight kg = {self.body_weight_kg} kg\n'
             f'Cycles : {len(self.cycles)} {' '.join(self.cycles.keys())}\n'
             f'Total nb of timepoints = {self.number_of_timepoints()}')
        return s

    @property
    def db_folder(self):
        if self._db_folder is None:
            fatal(f'Database folder is not defined')
        if not os.path.exists(self._db_folder):
            fatal(f'Database folder {self._db_folder} does not exist')
        return Path(os.path.abspath(self._db_folder))

    def __str__(self):
        return (f'{self.patient_id} '
                f'{self.body_weight_kg} kg - '
                f'{len(self.cycles)} cycles - '
                f'{self.number_of_timepoints()} timepoints')

    def number_of_timepoints(self):
        return np.array([len(cycle.timepoints) for cycle in self.cycles.values()]).sum()

    def get_cycle(self, cycle_id):
        if cycle_id not in self.cycles:
            self.cycles[cycle_id] = TreatmentCycle(self, cycle_id)
        return self.cycles[cycle_id]

    def add_dicom_ct(self, cycle_id, tp_id, folder_path):
        cycle = self.get_cycle(cycle_id)
        tp = cycle.get_timepoint(tp_id)
        tp.add_dicom_ct(folder_path)

    def write(self, filename=None):
        if filename is None:
            filename = self.json_path
        self._db_folder = Path(os.path.dirname(filename))
        os.makedirs(self._db_folder, exist_ok=True)
        with open(filename, "w") as f:
            db = self.as_dict()
            json.dump(db, f, indent=2)
        self.json_path = filename

    def read(self, filename):
        with open(filename, "r") as f:
            db = json.load(f)
            self.from_dict(db)
        self._db_folder = Path(os.path.dirname(filename))
        self.json_path = filename
        #self.check_folders()
        #self.check_files()

    def as_dict(self):
        db = {
            "patient_id": self.patient_id,
            "body_weight_kg": self.body_weight_kg,
            "cycles": [cycle.as_dict() for cycle in self.cycles.values()]
        }
        return db

    def from_dict(self, db):
        self.patient_id = db["patient_id"]
        self.body_weight_kg = db["body_weight_kg"]
        for cycle in db["cycles"]:
            cid = cycle["cycle_id"]
            tc = TreatmentCycle(self, cid).from_dict(cycle)
            self.cycles[cid] = tc


class TreatmentCycle:

    def __init__(self, db, cycle_id):
        self.db = db
        self.cycle_id = cycle_id
        self.timepoints = {}
        self.injection_activity_mbq = None
        self.injection_datetime = None
        self.injection_radionuclide = None

    def info(self):
        s = (f'Cycle id = {self.cycle_id}\n'
             f'Folder = {self.cycle_folder}\n'
             f'Injection activity mbq = {self.injection_activity_mbq}\n'
             f'Injection datetime = {self.injection_datetime}\n'
             f'Injection radionuclide = {self.injection_radionuclide}\n'
             f'Timepoints = {len(self.timepoints)}')
        return s

    def __str__(self):
        s = ''
        if len(self.timepoints) > 1:
            s = 's'
        return (f'{self.cycle_id} '
                f'{self.injection_activity_mbq} MBq - '
                f'{self.injection_datetime} - '
                f'{len(self.timepoints)} timepoint{s}')

    def get_timepoint(self, tp_id):
        if tp_id not in self.timepoints:
            self.timepoints[tp_id] = ImagingTimepoint(self, tp_id)
        return self.timepoints[tp_id]

    @property
    def cycle_folder(self):
        return self.db.db_folder / self.cycle_id

    def as_dict(self):
        return {
            "cycle_id": self.cycle_id,
            "injection_activity_mbq": self.injection_activity_mbq,
            "injection_datetime": self.injection_datetime,
            "injection_radionuclide": self.injection_radionuclide,
            "timepoints": [tp.as_dict() for tp in self.timepoints.values()]
        }

    def from_dict(self, db):
        self.injection_activity_mbq = db["injection_activity_mbq"]
        self.injection_datetime = db["injection_datetime"]
        self.injection_radionuclide = db["injection_radionuclide"]
        for tp in db["timepoints"]:
            tid = tp["timepoint_id"]
            timepoint = ImagingTimepoint(self, tid).from_dict(tp)
            self.timepoints[tid] = timepoint
        return self


class ImagingTimepoint:
    """
        Store filenames, not paths, paths are computed on the fly.
        The folders are build from cycle/timepoint
    """

    def __init__(self, cycle, tp_id):
        self.cycle = cycle
        self.timepoint_id = tp_id
        self.acquisition_datetime = None
        self._ct_image_filename = None
        self._spect_image_filename = None

    def info(self):
        s = (f'Timepoint id = {self.timepoint_id}\n'
             f'Folder = {self.tp_folder}\n'
             f'Acquisition date = {self.acquisition_datetime}\n'
             f'CT image = {self.ct_image_path}\n'
             f'SPECT image = {self.spect_image_path}')
        return s

    def __str__(self):
        return (f'{self.timepoint_id} '
                f'{self.acquisition_datetime} '
                f'{self.ct_image_filename} '
                f'{self.spect_image_filename}')

    def as_dict(self):
        return {
            "timepoint_id": self.timepoint_id,
            "ct_image_filename": self.ct_image_filename,
            "spect_image_filename": self.spect_image_filename,
            "acquisition_datetime": self.acquisition_datetime,
        }

    def from_dict(self, db):
        self.ct_image_filename = db["ct_image_filename"]
        self.spect_image_filename = db["spect_image_filename"]
        self.acquisition_datetime = db["acquisition_datetime"]
        return self

    @property
    def ct_image_filename(self):
        return self._ct_image_filename

    @ct_image_filename.setter
    def ct_image_filename(self, filename):
        # check if basename only
        if os.path.basename(filename) != filename:
            fatal(f'CT filename must be without any path, while it is {filename} '
                  f'(try {os.path.basename(filename)})')
        self._ct_image_filename = filename

    @property
    def spect_image_filename(self):
        return self._spect_image_filename

    @spect_image_filename.setter
    def spect_image_filename(self, filename):
        # check if basename only
        if os.path.basename(filename) != filename:
            fatal(f'SPECT filename must be without any path, while it is {filename} '
                  f'(try {os.path.basename(filename)})')
        self._spect_image_filename = filename

    @property
    def ct_image_path(self):
        return self.tp_folder / self.ct_image_filename

    @property
    def spect_image_path(self):
        return self.tp_folder / self.spect_image_filename

    @property
    def tp_folder(self):
        return self.cycle.cycle_folder / self.timepoint_id

    @property
    def time_from_injection_h(self):
        return rim.get_time_from_injection_h(self.cycle.injection_datetime, self.acquisition_datetime)

    @time_from_injection_h.setter
    def time_from_injection_h(self, value):
        if self.cycle.injection_datetime is None and self.acquisition_datetime is None:
            self.cycle.injection_datetime = "1970-01-01 00:00:00"
            d = datetime.datetime.strptime(self.injection_datetime, "%Y-%m-%d %H:%M:%S")
            self.acquisition_datetime = (d + datetime.timedelta(hours=value)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            fatal(f'Cannot set the time from injection since injection_datetime or acquisition_datetime exists')

    def set_ct(self,
               ct_input_path,
               ct_filename=None,
               mode='copy',
               exist_ok=False):
        self.set_image(ct_input_path, 'ct_image', ct_filename, mode, exist_ok)

    def set_spect(self,
                  spect_input_path,
                  spect_filename=None,
                  mode='copy',
                  exist_ok=False):
        self.set_image(spect_input_path, 'spect_image', spect_filename, mode, exist_ok)

    def set_image(self,
                  input_image_path,
                  attribute_name,  # ct_image_filename or spect_image_filename
                  image_filename=None,
                  mode='copy',
                  exist_ok=False):
        """
        Copy or move a ct or a spect
        """
        # consider the image filename
        if image_filename is None:
            folder, filename = os.path.split(input_image_path)
            setattr(self, f"{attribute_name}_filename", filename)
        else:
            setattr(self, f"{attribute_name}_filename", image_filename)
        # create the dirs if needed
        path = os.path.dirname(getattr(self, f"{attribute_name}_path"))
        os.makedirs(path, exist_ok=True)
        # check if already exist
        if not exist_ok and os.path.exists(path):
            fatal(f'File image {path} already exists')
        # copy or move the image
        rim.copy_or_move_image(input_image_path, getattr(self, f"{attribute_name}_path"), mode)
