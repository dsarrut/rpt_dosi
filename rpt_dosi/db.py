from . import dicom_utils as rdcm
from . import images as rim
from . import helpers as rhe
from . import metadata as rmd
import shutil
import json
from box import Box
from datetime import datetime
import numpy as np
from .helpers import fatal
import os
from pathlib import Path


def OLD_db_update_injection(db, dicom_ds, cycle_id):
    # extract injection
    rad = rdcm.dicom_read_injection(dicom_ds)

    # create cycle if not exist
    if cycle_id not in db["cycles"]:
        db["cycles"][cycle_id] = {}

    # update the db: cycle
    # FIXME maybe check already exist ?
    cycle = db["cycles"][cycle_id]
    cycle["injection"].update(rad)

    return db


def OLD_db_update_acquisition(db, dicom_ds, cycle_id, tp_id):
    # extract the date/time
    dt = rdcm.dicom_read_acquisition_datetime(dicom_ds)

    cycle = db["cycles"][cycle_id]

    # create cycle if not exist
    if tp_id not in cycle["acquisitions"]:
        cycle["acquisitions"][tp_id] = {}

    # update the db: acquisition
    acqui = cycle["acquisitions"][tp_id]
    acqui.update(dt)

    return db


def OLD_db_update_cycle_rois_activity(cycle):
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


def OLD_db_load(filename):
    # open db as a dict
    f = open(filename, "r")
    db = Box(json.load(f))
    return db


def OLD_db_save(db, output, db_file=None):
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


def OLD_db_get_tac(cycle, roi_id):
    times = []
    activities = []
    for acq in cycle.acquisitions.values():
        if roi_id in acq.activity.keys():
            activities.append(acq.activity[roi_id].sum)
            d = db_get_time_interval(cycle, acq)
            times.append(d)
    return np.array(times), np.array(activities)


class PatientTreatmentDatabase(rmd.ClassWithMetaData):
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

    _metadata_fields = {'patient_id': str,
                        'body_weight_kg': float}

    def __init__(self, filename, create=False, sync_metadata_image=False):
        # metadata
        super().__init__()
        self.patient_id = None
        self.body_weight_kg = None
        self.cycles = {}
        # stores the initial json file path (only used in write)
        self._db_filepath = None
        # db_folder is the base folder where the data should be
        self._db_data_path = None
        # read or create json file
        if os.path.exists(filename):
            self.read(filename, sync_metadata_image=sync_metadata_image)
        else:
            if create:
                self.write(filename, sync_metadata_image=sync_metadata_image)
            else:
                fatal(f'The database file {filename} does not exist')

    def info(self):
        ctp = ''
        for cycle in self.cycles.values():
            ctp += f'{cycle.cycle_id} ({len(cycle.timepoints)})   '
        s = (f'Patient id = {self.patient_id}\n'
             f'Data folder = {self.db_data_path}\n'
             f'Body weight kg = {self.body_weight_kg} kg\n'
             f'Cycles {len(self.cycles)} = {ctp}\n'
             f'Total nb of timepoints = {self.number_of_timepoints()}\n'
             f'Total nb of images = {self.number_of_images()}\n'
             f'Total nb of rois = {self.number_of_rois()}')
        return s

    @property
    def db_data_path(self):
        if self._db_data_path is None:
            fatal(f'Database folder is not defined')
        if not os.path.exists(self._db_data_path):
            fatal(f'Database folder {self._db_data_path} does not exist')
        return Path(self._db_data_path)

    @property
    def db_filepath(self):
        return self._db_filepath

    @db_filepath.setter
    def db_filepath(self, value):
        self._db_filepath = os.path.abspath(value)
        self._db_data_path = os.path.abspath(os.path.dirname(value))
        os.makedirs(self._db_data_path, exist_ok=True)

    def __str__(self):
        return (f'{self.patient_id} '
                f'{self.body_weight_kg} kg - '
                f'{len(self.cycles)} cycles - '
                f'{self.number_of_timepoints()} timepoints')

    def number_of_timepoints(self):
        return np.array([len(cycle.timepoints) for cycle in self.cycles.values()]).sum()

    def number_of_rois(self):
        n = 0
        for cycle in self.cycles.values():
            for tp in cycle.timepoints.values():
                n += len(tp.rois)
        return n

    def number_of_images(self):
        n = 0
        for cycle in self.cycles.values():
            for tp in cycle.timepoints.values():
                n += len(tp.images)
        return n

    def get_cycle(self, cycle_id):
        if cycle_id not in self.cycles:
            self.cycles[cycle_id] = TreatmentCycle(self, cycle_id)
        return self.cycles[cycle_id]

    def __getitem__(self, key):
        return self.get_cycle(key)

    def add_cycle(self, cycle):
        if cycle.cycle_id in self.cycles.keys():
            fatal(f'The cycle "{cycle.cycle_id}" already exists in this db: {self}')
        self.cycles[cycle.cycle_id] = cycle
        return cycle

    def remove_cycle(self, cycle_id):
        if cycle_id not in self.cycles:
            fatal(f'The cycle "{cycle_id}" does not exist in this db: {self.cycles.keys()}')
        self.cycles.pop(cycle_id)

    def add_new_cycle(self, cycle_id):
        cycle = TreatmentCycle(self, cycle_id)
        return self.add_cycle(cycle)

    def add_dicom_ct(self, cycle_id, tp_id, folder_path):
        cycle = self.get_cycle(cycle_id)
        tp = cycle.get_timepoint(tp_id)
        tp.add_dicom_ct(folder_path)

    def write(self, filename=None, sync_metadata_image=True):
        if filename is None:
            filename = self.db_filepath
        self.db_filepath = filename
        if sync_metadata_image:
            self.sync_metadata_images()
        self.save_to_json(self.db_filepath)
        if sync_metadata_image:
            self.write_metadata_images()

    def write_metadata_images(self):
        for cycle in self.cycles.values():
            cycle.write_metadata_images()

    def sync_metadata_images(self, force_flag="no"):
        for cycle in self.cycles.values():
            cycle.sync_metadata_images(force_flag)

    def read(self, filename, sync_metadata_image):
        if not os.path.exists(filename):
            fatal(f'Database file {filename} does not exist')
        self._db_data_path = Path(os.path.abspath(os.path.dirname(filename)))
        self.db_filepath = filename
        self.load_from_json(filename)
        if sync_metadata_image:
            for cycle in self.cycles.values():
                cycle.sync_metadata_images()
        # self.check_folders()
        # self.check_files()

    def to_dict(self):
        data = super().to_dict()
        data["cycles"] = {cycle.cycle_id: cycle.to_dict() for cycle in self.cycles.values()}
        return data

    def from_dict(self, data):
        super().from_dict(data)
        for cid, cycle in data["cycles"].items():
            tc = TreatmentCycle(self, cid).from_dict(cycle)
            self.cycles[cid] = tc

    def check_folders(self):
        is_ok = True
        for cycle in self.cycles.values():
            is_ok = cycle.check_folders() and is_ok
        return is_ok

    def check_files(self):
        is_ok = True
        for cycle in self.cycles.values():
            is_ok = cycle.check_files() and is_ok
        return is_ok


class TreatmentCycle(rmd.ClassWithMetaData):
    _metadata_fields = {  # 'cycle_id': str,
        'injection_activity_mbq': float,
        'injection_datetime': str,
        'injection_radionuclide': str
    }

    def __init__(self, db, cycle_id):
        # this cycle belong to this db
        super().__init__()
        self.db = db
        # metadata
        self.cycle_id = cycle_id
        self.injection_activity_mbq = None
        self._injection_datetime = None
        self.injection_radionuclide = None
        self.timepoints = {}
        # create folder
        os.makedirs(self.cycle_path, exist_ok=True)

    def info(self):
        s = (f'Cycle id = {self.cycle_id}\n'
             f'Folder = {self.cycle_path}\n'
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

    @property
    def injection_datetime(self):
        return self._injection_datetime

    @injection_datetime.setter
    def injection_datetime(self, value):
        if value is None:
            self._injection_datetime = None
            return
        self._injection_datetime = rim.convert_datetime(value)

    def get_timepoint(self, tp_id):
        if tp_id not in self.timepoints:
            self.timepoints[tp_id] = ImagingTimepoint(self, tp_id)
        return self.timepoints[tp_id]

    def __getitem__(self, key):
        return self.get_timepoint(key)

    def add_timepoint(self, tp):
        if tp.timepoint_id in self.timepoints.keys():
            fatal(f'The timepoint "{tp.timepoint_id}" already exists in this db: {self.timepoints.keys()}')
        if tp.cycle != self:
            fatal(f'The cycle of the timepoint [{tp.cycle}] is different than this cycle: [{self}]')
        self.timepoints[tp.timepoint_id] = tp
        return tp

    def add_new_timepoint(self, tp_id):
        tp = ImagingTimepoint(self, tp_id)
        return self.add_timepoint(tp)

    @property
    def cycle_path(self):
        return self.db.db_data_path / self.cycle_id

    def to_dict(self):
        data = super().to_dict()
        data["timepoints"] = {tp.timepoint_id: tp.to_dict() for tp in self.timepoints.values()}
        return data

    def from_dict(self, data):
        super().from_dict(data)
        for tid, tp in data["timepoints"].items():
            timepoint = ImagingTimepoint(self, tid).from_dict(tp)
            self.timepoints[tid] = timepoint
        return self

    def sync_metadata_images(self, force_flag="no"):
        for tp in self.timepoints.values():
            tp.sync_metadata_images(force_flag)

    def write_metadata_images(self):
        for tp in self.timepoints.values():
            tp.write_metadata_images()

    def check_folders(self):
        if not os.path.exists(self.cycle_path):
            print(f'Error the folder for cycle {self.cycle_id} '
                  f'does not exist (expected {self.cycle_path})')
            return False
        is_ok = True
        for tp in self.timepoints.values():
            is_ok = tp.check_folders() and is_ok
        return is_ok

    def check_files(self):
        is_ok = True
        for tp in self.timepoints.values():
            is_ok = tp.check_files() and is_ok
        return is_ok


class ImagingTimepoint(rmd.ClassWithMetaData):
    """
        Store filenames, not paths, paths are computed on the fly.
        The folders are build from db/cycle/timepoint
    """
    _metadata_fields = {
        'acquisition_datetime': str
    }

    def __init__(self, cycle, tp_id):
        # this timepoint belong to this cycle
        super().__init__()
        self.cycle = cycle
        # metadata
        self.timepoint_id = tp_id
        self._acquisition_datetime = None
        # several images
        self.images = {}
        # several rois (in the rois folder)
        self.rois = {}
        # create folder
        os.makedirs(self.timepoint_path, exist_ok=True)
        os.makedirs(self.rois_path, exist_ok=True)

    def info(self):
        s = (f'Timepoint id = {self.timepoint_id}\n'
             f'Folder = {self.timepoint_path}\n'
             f'Acquisition date = {self.acquisition_datetime}\n'
             f'Images = {len(self.images)} {" ".join(self.images.keys())}\n'
             f'ROIs = {len(self.rois)} {" ".join(self.rois.keys())}')
        return s

    def __str__(self):
        sr = ''
        if len(self.rois) > 1:
            sr = 's'
        si = ''
        if len(self.images) > 1:
            si = 's'
        return (f'{self.timepoint_id} '
                f'date={self.acquisition_datetime} '
                f'-- {len(self.images)} image{si} '
                f'-- {len(self.rois)} roi{sr}')

    def to_dict(self):
        data = super().to_dict()
        data["rois"] = {}
        data["images"] = {}
        for key, roi in self.rois.items():
            data["rois"][key] = roi.to_dict()
        for key, image in self.images.items():
            data["images"][key] = image.to_dict()
        return data

    def from_dict(self, data):
        super().from_dict(data)
        for key, value in data['rois'].items():
            r = ROIInfo_OLD()
            r.from_dict(value)
            self.rois[key] = r
        for key, value in data['images'].items():
            filepath = self.timepoint_path / value['filename']
            im = rim.build_meta_image(value['image_type'], filepath, create=True)
            im.from_dict(value)
            self.images[key] = im
        return self

    @property
    def acquisition_datetime(self):
        return self._acquisition_datetime

    @acquisition_datetime.setter
    def acquisition_datetime(self, value):
        if value is None:
            self._acquisition_datetime = None
            return
        self._acquisition_datetime = rim.convert_datetime(value)

    def sync_metadata_images(self, force_flag="no"):
        for image_name in self.images.keys():
            self.sync_metadata_image(image_name, force_flag)

    def sync_metadata_image(self, image_name, force_flag="no"):
        image = self.get_metaimage(image_name)
        self._update_field(image, self.cycle, 'injection_activity_mbq'), force_flag
        self._update_field(image, self.cycle, 'injection_datetime', force_flag)
        self._update_field(image, self.cycle.db, 'body_weight_kg', force_flag)
        self._update_field(image, self, 'acquisition_datetime', force_flag)

    def write_metadata_images(self):
        for image in self.images.values():
            image.write_metadata()

    def _update_field(self, image, element_db, tag_name, force_flag="no"):
        # check the tag name is available in the objects
        try:
            getattr(element_db, tag_name)
        except:
            return
        try:
            getattr(image, tag_name)
        except:
            return
        # do nothing if the value is the same
        if getattr(element_db, tag_name) == getattr(image, tag_name):
            return
        # force value to the image
        if force_flag == "force_to_image":
            setattr(image, tag_name, getattr(element_db, tag_name))
            return
        # force value to the db
        if force_flag == "force_to_db":
            setattr(element_db, tag_name, getattr(image, tag_name))
            return
        # if one is None
        if getattr(element_db, tag_name) is not None and getattr(image, tag_name) is None:
            setattr(image, tag_name, getattr(element_db, tag_name))
            return
        if getattr(element_db, tag_name) is None and getattr(image, tag_name) is not None:
            setattr(element_db, tag_name, getattr(image, tag_name))
            return
        # warning : two different values
        if force_flag == "no":
            if getattr(element_db, tag_name) is not None and getattr(image, tag_name) is not None:
                # getattr(element_db, tag_name) = getattr(image, tag_name)
                rhe.warning(f'Warning : incoherent {tag_name}, db = {getattr(element_db, tag_name)} '
                            f'while image = {getattr(image, tag_name)} ({image})')
                return
        fatal(f'Cannot update {tag_name} field : force_flag = {force_flag} while must '
              f'be "no" or "force_to_image" or "force_to_db"')

    @property
    def timepoint_path(self):
        return self.cycle.cycle_path / self.timepoint_id

    @property
    def rois_path(self):
        return self.timepoint_path / "rois"

    def get_roi_info(self, roi_id):
        if roi_id not in self.rois:
            fatal(f'Cannot find ROI {roi_id} in the list of rois {self.rois.keys()}')
        return self.rois[roi_id]

    def get_roi_path(self, roi_id):
        return self.rois_path / self.get_roi_info(roi_id).filename

    def get_metaimage(self, image_name):
        if image_name not in self.images:
            fatal(f'Cannot find image {image_name} in the list of images {self.images.keys()}')
        return self.images[image_name]

    def get_image_filepath(self, image_name):
        return self.get_metaimage(image_name).image_filepath
        # return self.timepoint_path / self.get_metaimage(image_name).filename

    @property
    def time_from_injection_h(self):
        return rim.get_time_from_injection_h(self.cycle.injection_datetime, self.acquisition_datetime)

    @time_from_injection_h.setter
    def time_from_injection_h(self, value):
        self.cycle.injection_datetime, self.acquisition_datetime = (
            rim.set_time_from_injection_h(self.cycle.injection_datetime, self.acquisition_datetime, value))

    def add_image_from_file(self,
                            image_name,
                            input_path,
                            image_type=None,
                            filename=None,
                            mode='copy',
                            unit=None,
                            exist_ok=False):
        if image_name in self.images:
            fatal(f'Cannot add image {image_name} since it already exists')
        # get the filename
        if filename is None:
            filename = os.path.basename(input_path)
        # copy or move the initial image
        dest_path = self.timepoint_path / filename
        if not exist_ok and os.path.exists(dest_path):
            fatal(f'File image {dest_path} already exists')
        rim.copy_or_move_image(input_path, dest_path, mode)
        im = rim.build_meta_image(image_type, filepath=dest_path, create=True)
        # manage the unit if it is not in the initial image
        if unit is None:
            # warning the image type is ignored, we only look for the unit
            source_img = rim.read_image_header_only(input_path)
            if source_img.unit is not None:
                im.unit = source_img.unit
        else:
            im.unit = unit
        # add it
        self.add_image(image_name, im)

    def add_image(self, image_name, meta_image):
        if image_name in self.images:
            fatal(f'Cannot add image {image_name} since it already exists')
        # check path
        fp = meta_image.image_filepath
        dest_path = self.timepoint_path / meta_image.filename
        if str(fp) != str(dest_path):
            fatal(f'Cannot add image {image_name}, the filepath "{fp}" '
                  f'is not in the db (should be {dest_path})')
        # insert
        try:
            self.images[image_name] = meta_image
            # update the metadata image and db should be the same
            self.sync_metadata_image(image_name)
            meta_image.write_metadata()
        except rhe.Rpt_Error:
            # if there is an error, remove the image and raise the error again
            self.images.pop(image_name)
            raise

    def add_rois(self, roi_list, mode='copy', exist_ok=False):
        for roi in roi_list:
            self.add_roi(roi['roi_id'], roi['filename'], mode, exist_ok)

    def add_roi(self, roi_id, input_path, mode="copy", exist_ok=False):
        # compute the new filename as roi_id.extension
        _, extension = rhe.get_basename_and_extension(input_path)
        filename = f'{roi_id}{extension}'
        filename = filename.replace(' ', '_')
        try:
            self.rois[roi_id] = ROIInfo_OLD(roi_id, filename)
            # get the dest path
            dest_path = self.get_roi_path(roi_id)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            # check if already exist
            if not exist_ok and os.path.exists(dest_path):
                fatal(f'File image {dest_path} already exists')
            rim.copy_or_move_image(input_path, dest_path, mode)
            self.update_roi_json_from_db_info(roi_id)
        except rhe.Rpt_Error:
            # if there is an error, remove the image and raise the error again
            self.rois.pop(roi_id)
            raise

    def update_roi_json_from_db_info(self, roi_id):
        dest_path = self.get_roi_path(roi_id)
        if os.path.exists(dest_path):
            spect = rim.MetaImageROI(dest_path, roi_id)
            spect.filename = str(dest_path)
            spect.read_image_header()
            spect.write_metadata()

    def check_folders(self):
        if not os.path.exists(self.timepoint_path):
            print(f'Error the folder for timepoint {self.timepoint_id} '
                  f'does not exist (expected {self.timepoint_path})')
            return False
        if not os.path.exists(self.timepoint_path / "rois"):
            print(f'Error the ROI folder for timepoint {self.timepoint_id} '
                  f'does not exist (expected {self.timepoint_path / "rois"})')
            return False
        return True

    def check_files(self):
        for image in self.images.values():
            if not os.path.exists(self.get_image_filepath(image.image_name)):
                print(f'Error the image {image.image_name} does not exist: {self.get_image_filepath(image.image_name)}')
                return False
        is_ok = True
        for roi in self.rois:
            if not os.path.exists(self.get_roi_path(roi)):
                print(f'Error the roi {self.get_roi_path(roi)} '
                      f'does not exist')
                is_ok = False
        # TODO check mhd raw files !!
        return is_ok


class ROIInfo_OLD(rmd.ClassWithMetaData):
    _metadata_fields = {"filename": str}

    def __init__(self, roi_id=None, filename=None):
        super().__init__()
        self.roi_id = roi_id
        self.filename = filename
