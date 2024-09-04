from . import images as rim
from . import metadata as rmd
from . import utils as rhe
from .utils import fatal
from datetime import datetime
import numpy as np
import os
from pathlib import Path


def db_get_time_interval(cycle, acquisition):
    idate = datetime.strptime(cycle.injection.datetime, "%Y-%m-%d %H:%M:%S")
    adate = datetime.strptime(acquisition.datetime, "%Y-%m-%d %H:%M:%S")
    hours_diff = (adate - idate).total_seconds() / 3600
    return hours_diff


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
        self._db_file_path = None
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
    def db_file_path(self):
        return self._db_file_path

    @db_file_path.setter
    def db_file_path(self, value):
        self._db_file_path = os.path.abspath(value)
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
            # self.cycles[cycle_id] = CycleTreatmentDatabase(self, cycle_id)
            fatal(f'Cannot find the cycle named "{cycle_id}". Available cycles are: {self.cycles.keys()}')
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
        cycle = CycleTreatmentDatabase(self, cycle_id)
        return self.add_cycle(cycle)

    def add_dicom_ct(self, cycle_id, tp_id, folder_path):
        cycle = self.get_cycle(cycle_id)
        tp = cycle.get_timepoint(tp_id)
        tp.add_dicom_ct(folder_path)

    def write(self, filename=None, sync_metadata_image=True, sync_policy="auto"):
        if filename is None:
            filename = self.db_file_path
        self.db_file_path = filename
        if sync_metadata_image:
            self.sync_metadata_images(sync_policy)
        self.save_to_json(self.db_file_path)
        if sync_metadata_image:
            self.write_metadata_images()

    def write_metadata_images(self):
        for cycle in self.cycles.values():
            cycle.write_metadata_images()

    def sync_metadata_images(self, sync_policy="auto"):
        for cycle in self.cycles.values():
            cycle.sync_metadata_images(sync_policy)

    def read(self, filename, sync_metadata_image):
        if not os.path.exists(filename):
            fatal(f'Database file {filename} does not exist')
        self._db_data_path = Path(os.path.abspath(os.path.dirname(filename)))
        self.db_file_path = filename
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
        df = self._db_data_path
        super().from_dict(data)
        for cid, cycle in data["cycles"].items():
            tc = CycleTreatmentDatabase(self, cid).from_dict(cycle)
            self.cycles[cid] = tc

    def check_folders_exist(self):
        ok = True
        msg = ''
        for cycle in self.cycles.values():
            b, msg = cycle.check_folders_exist()
            ok = b and ok
        return ok, msg

    def check_files_exist(self):
        ok = True
        msg = ''
        for cycle in self.cycles.values():
            b, m = cycle.check_files_exist()
            ok = b and ok
            msg += m
        return ok, msg

    def check_files_metadata(self):
        ok = True
        msg = ''
        for cycle in self.cycles.values():
            b, m = cycle.check_files_metadata()
            ok = b and ok
            msg += m
        return ok, msg


class CycleTreatmentDatabase(rmd.ClassWithMetaData):
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
            self.timepoints[tp_id] = TimepointTreatmentDatabase(self, tp_id)
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
        tp = TimepointTreatmentDatabase(self, tp_id)
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
            timepoint = TimepointTreatmentDatabase(self, tid).from_dict(tp)
            self.timepoints[tid] = timepoint
        return self

    def sync_metadata_images(self, sync_policy="auto"):
        for tp in self.timepoints.values():
            tp.sync_metadata_images(sync_policy)

    def write_metadata_images(self):
        for tp in self.timepoints.values():
            tp.write_metadata_images()

    def check_folders_exist(self):
        ok = True
        msg = ''
        if not os.path.exists(self.cycle_path):
            msg += (f'Error the folder for cycle {self.cycle_id} '
                    f'does not exist (expected {self.cycle_path})')
            ok = False
        for tp in self.timepoints.values():
            b, m = tp.check_folders_exist()
            msg += m
            ok = b and ok
        return ok, msg

    def check_files_exist(self):
        ok = True
        msg = ''
        for tp in self.timepoints.values():
            b, m = tp.check_files_exist()
            ok = b and ok
            msg += m
        return ok, msg

    def check_files_metadata(self):
        ok = True
        msg = ''
        for tp in self.timepoints.values():
            b, m = tp.check_files_metadata()
            ok = b and ok
            msg += m
        return ok, msg


class TimepointTreatmentDatabase(rmd.ClassWithMetaData):
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
            file_path = self.rois_path / value['filename']
            roi = rim.MetaImageROI(image_path=file_path,
                                   name=value['name'],
                                   create=True,
                                   reading_mode='metadata_only')
            roi.from_dict(value)
            # we set the roi path to the current data folder
            roi.image_file_path = file_path
            self.rois[key] = roi
        for key, value in data['images'].items():
            file_path = self.timepoint_path / value['filename']
            im = rim.read_metaimage(file_path, reading_mode='metadata_only')
            im.from_dict(value)
            # we set the image path to the current data folder
            im.image_file_path = file_path
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

    def sync_metadata_images(self, sync_policy="auto"):
        for image_name in self.images.keys():
            self.sync_metadata_image(image_name, sync_policy)
        for roi_name in self.rois.keys():
            self.sync_metadata_roi(roi_name, sync_policy)

    def sync_metadata_image(self, image_name, sync_policy="auto"):
        image = self.get_metaimage(image_name)
        rmd.sync_field_image_db(image, self.cycle, 'injection_activity_mbq', sync_policy)
        rmd.sync_field_image_db(image, self.cycle, 'injection_datetime', sync_policy)
        rmd.sync_field_image_db(image, self.cycle.db, 'body_weight_kg', sync_policy)
        rmd.sync_field_image_db(image, self, 'acquisition_datetime', sync_policy)

    def sync_metadata_roi(self, roi_name, sync_policy="auto"):
        roi = self.get_roi(roi_name)
        if roi_name == roi.name:
            return
        if sync_policy == "force_to_image":
            roi.name = roi_name
            return
        if sync_policy == "force_to_db":
            self.add_roi(roi)
            return
        if roi_name is None:  # not possible
            self.add_roi(roi)
            return
        if roi.name is None:  # not possible
            roi.name = roi_name
            return
        if sync_policy == "auto":
            rhe.warning(f'Warning : incoherent roi name {roi.name}, db = {roi_name}')
            return
        fatal(f'Cannot update {roi_name}: sync_policy = {sync_policy} while must '
              f'be "auto" or "force_to_image" or "force_to_db"')
        pass

    def write_metadata_images(self):
        for image in self.images.values():
            image.write_metadata()

    @property
    def timepoint_path(self):
        return self.cycle.cycle_path / self.timepoint_id

    @property
    def rois_path(self):
        return self.timepoint_path / "rois"

    def get_roi(self, roi_id):
        if roi_id not in self.rois:
            fatal(f'Cannot find ROI {roi_id} in the list of rois {self.rois.keys()}')
        return self.rois[roi_id]

    def get_roi_path(self, roi_id):
        return self.rois_path / self.get_roi(roi_id).filename

    def get_metaimage(self, image_name):
        if image_name not in self.images:
            fatal(f'Cannot find image {image_name} in the list of images {self.images.keys()}')
        return self.images[image_name]

    def get_image_file_path(self, image_name):
        return self.get_metaimage(image_name).image_file_path

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
                            file_exist_ok=False):
        if image_name in self.images:
            fatal(f'Cannot add image {image_name} since it already exists')
        # get the filename
        if filename is None:
            filename = os.path.basename(input_path)
        # copy or move the initial image
        dest_path = self.timepoint_path / filename
        if not file_exist_ok and os.path.exists(dest_path):
            fatal(f'File image {dest_path} already exists')
        if input_path != dest_path:
            rim.copy_or_move_image(input_path, dest_path, mode)
        # with initial metadata?
        if rim.metadata_exists(input_path):
            im = rim.read_metaimage(input_path, reading_mode='metadata_only')
            im.image_file_path = dest_path
            if image_type is not None and image_type != im.image_type:
                fatal(f'Cannot add the read image, the image type is {im.image_type}'
                      f' while {image_type} is expected')
        else:
            im = rim.new_metaimage(image_type,
                                   file_path=dest_path,
                                   unit=unit,
                                   reading_mode='metadata_only')
            print(im)
        # add it
        return self.add_image(image_name, im)

    def add_image(self, image_name, meta_image):
        if image_name in self.images:
            fatal(f'Cannot add image {image_name} since it already exists')
        # check path
        fp = meta_image.image_file_path
        dest_path = self.timepoint_path / meta_image.filename
        if str(fp) != str(dest_path):
            fatal(f'Cannot add image {image_name}, the file_path "{fp}" '
                  f'is not in the db (should be {dest_path})')
        # insert
        try:
            self.images[image_name] = meta_image
            # update the metadata image and db should be the same
            self.sync_metadata_image(image_name, sync_policy='auto')
            meta_image.write_metadata()
        except rhe.RptError:
            # if there is an error, remove the image and raise the error again
            self.images.pop(image_name)
            raise
        return meta_image

    def add_rois(self, roi_list, mode='copy', exist_ok=False):
        for roi in roi_list:
            self.add_roi_from_file(roi['roi_id'], roi['filename'], mode, exist_ok)

    def add_roi(self, roi):
        if roi.name in self.rois:
            fatal(f'Cannot add roi {roi.name} since it already exists')
        # check path
        fp = roi.image_file_path
        dest_path = self.rois_path / roi.filename
        if str(fp) != str(dest_path):
            fatal(f'Cannot add roi {roi.name}, the file_path "{fp}" '
                  f'is not in the db (should be {dest_path})')
        # insert
        try:
            self.rois[roi.name] = roi
            # update the metadata image and db should be the same
            self.sync_metadata_roi(roi.name)
            roi.write_metadata()
        except rhe.RptError:
            # if there is an error, remove the image and raise the error again
            self.rois.pop(roi.name)
            raise
        return roi

    def add_roi_from_file(self, roi_id, input_path, mode="copy", exist_ok=False):
        # compute the new filename as roi_id.extension
        _, extension = rhe.get_basename_and_extension(input_path)
        filename = f'{roi_id}{extension}'
        filename = filename.replace(' ', '_')
        # copy or move the initial image
        dest_path = self.rois_path / filename
        if not exist_ok and os.path.exists(dest_path):
            fatal(f'File image {dest_path} already exists')
        rim.copy_or_move_image(input_path, dest_path, mode)
        # with initial metadata?
        if rim.metadata_exists(input_path):
            roi = rim.read_roi(input_path)
            roi.image_file_path = dest_path
            roi.name = roi_id
        else:
            roi = rim.new_metaimage('ROI',
                                    file_path=dest_path,
                                    name=roi_id,
                                    reading_mode='metadata_only')
        # add it
        return self.add_roi(roi)

    def check_folders_exist(self):
        msg = ''
        ok = True
        if not os.path.exists(self.timepoint_path):
            msg += (f'Error the folder for timepoint {self.timepoint_id} '
                    f'does not exist (expected {self.timepoint_path})')
            ok = False
        if not os.path.exists(self.timepoint_path / "rois"):
            msg += (f'Error the ROI folder for timepoint {self.timepoint_id} '
                    f'does not exist (expected {self.timepoint_path / "rois"})')
            ok = False
        return ok, msg

    def check_files_exist(self):
        msg = ''
        ok = True
        for image in self.images.values():
            if not os.path.exists(image.image_file_path):
                msg += f'{self.cycle.cycle_id} {self.timepoint_id} The image {image.image_name} does not exist: {self.get_image_file_path(image.image_name)}'
                ok = False
        for roi in self.rois:
            if not os.path.exists(self.get_roi_path(roi)):
                msg += (f'{self.cycle.cycle_id} {self.timepoint_id} The roi '
                        f'{self.get_roi_path(roi)} does not exist')
                ok = False
        return ok, msg
        # TODO check mhd raw files !!

    def check_files_metadata(self):
        msg = ''
        ok = True
        # check images
        for k, image in self.images.items():
            o, m = image.check_file_metadata()
            if m != '':
                m = f'[{k}: {m}] '
            msg += m
            ok = o and ok
            ok, msg = rmd.sync_field_image_db_check(image, self.cycle, 'injection_activity_mbq', ok, msg)
            ok, msg = rmd.sync_field_image_db_check(image, self.cycle, 'injection_datetime', ok, msg)
            ok, msg = rmd.sync_field_image_db_check(image, self.cycle.db, 'body_weight_kg', ok, msg)
            ok, msg = rmd.sync_field_image_db_check(image, self, 'acquisition_datetime', ok, msg)
        # check roi
        for k, roi in self.rois.items():
            o, m = roi.check_file_metadata()
            if m != '':
                m = f'[{k}: {m}] '
            msg += m
            ok = o and ok
            if roi.name != k:
                ok = False
                msg += f'The roi name {k} is different in the file {roi.name}\n'
        msg = msg.rstrip('\n')
        return ok, msg


def create_test_db(data_folder, db_file_path):
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
    db = PatientTreatmentDatabase(db_file_path, create=True)
    cycle = CycleTreatmentDatabase(db, "cycle1")
    db.add_cycle(cycle)
    db.add_new_cycle('cycle2')
    db.add_new_cycle('cycle3')
    tp = cycle.add_new_timepoint("tp1")
    cycle.add_new_timepoint("tp2")
    cycle.add_new_timepoint("tp3")

    # add images
    tp.add_image_from_file("ct",
                           data_folder / "ct_8mm.nii.gz",
                           image_type="CT",
                           filename="ct1.nii.gz",
                           mode="copy",
                           file_exist_ok=True)
    tp.add_image_from_file("spect",
                           data_folder / "spect_8.321mm.nii.gz",
                           image_type="SPECT",
                           filename="spect.nii.gz",
                           mode="copy",
                           unit='Bq',
                           file_exist_ok=True)

    tp.add_image_from_file("spect2",  # this one has a json, not need for unit
                           data_folder / "spect_10mm_with_json.nii.gz",
                           image_type="SPECT",
                           filename="spect2.nii.gz",
                           mode="copy",
                           file_exist_ok=True)

    tp.add_image_from_file("pet",
                           data_folder / "ct_8mm.nii.gz",
                           image_type="PET",
                           filename="pet.nii.gz",
                           unit='Bq/mL',
                           mode="copy",
                           file_exist_ok=True)

    tp.add_roi_from_file("liver",
                         data_folder / "rois" / "liver.nii.gz",
                         mode="copy",
                         exist_ok=True)
    tp.add_roi_from_file("left kidney",
                         data_folder / "rois" / "kidney_left.nii.gz",
                         mode="copy",
                         exist_ok=True)

    db.write()
    return db


def compute_time_activity_curve(cycle, roi_names, spect_name='spect'):
    # init the TAC
    times = {}
    activities = {}
    for roi_name in roi_names:
        times[roi_name] = []
        activities[roi_name] = []

    # Get all activities and group per ROI
    for tp in cycle.timepoints.values():
        spect = tp.images[spect_name]
        spect.read()
        spect.convert_to_bq()
        time_h = rim.get_time_from_injection_h(cycle.injection_datetime,
                                               spect.acquisition_datetime)
        for roi_name in roi_names:
            roi = tp.get_roi(roi_name)
            res = rim.image_roi_stats(roi, spect, resample_like='spect')
            times[roi.name].append(time_h)
            # convert to MBq
            activities[roi.name].append(res['sum'] / 1e6)
    return times, activities
