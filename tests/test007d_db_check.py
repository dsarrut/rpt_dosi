#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import rpt_dosi.utils as he
import rpt_dosi.db as rdb
import shutil
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test007d")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # create a db from scratch
    start_test(f"Create a new database with cycle and TP")
    db_file_path = output_folder / "db007d.json"
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
    db = rdb.PatientTreatmentDatabase(db_file_path, create=True)
    db.add_new_cycle("cycle2")
    cycle = db.add_new_cycle("cycle1")
    cycle.add_new_timepoint("tp1")
    tp = cycle.add_new_timepoint("tp2")

    # add images
    tp.add_image_from_file("ct",
                           data_folder / "ct_8mm.nii.gz",
                           image_type="CT",
                           filename="ct1.nii.gz",
                           mode="copy",
                           file_exist_ok=True)
    im = tp.add_image_from_file("spect",
                                data_folder / "spect_8.321mm.nii.gz",
                                image_type="SPECT",
                                filename="spect.nii.gz",
                                mode="copy",
                                unit='Bq',
                                file_exist_ok=True)
    # add rois
    roi_list = [
        {'roi_id': 'colon', 'filename': data_folder / 'rois' / 'colon.nii.gz'},
        {'roi_id': 'skull', 'filename': data_folder / 'rois' / 'skull.nii.gz'},
        {'roi_id': 'liver', 'filename': data_folder / 'rois' / 'colon.nii.gz'},
        {'roi_id': 'spleen', 'filename': data_folder / 'rois' / 'colon.nii.gz'},
    ]
    tp.add_rois(roi_list, exist_ok=True)
    print(db.info())
    ok = db.number_of_rois() == 4 and db.number_of_images() == 2
    stop_test(ok, f'Create db: {ok}')

    # check if all files are there
    start_test(f"Check if all folders/files are there")
    b, m = db.check_folders_exist()
    stop_test(b, f'Check folders {b} {m}')
    b, m = db.check_files_exist()
    stop_test(b, f'Check files {b} {m}')

    # mv files
    f = tp.rois['skull'].image_file_path
    shutil.move(f, f + '.back')
    b, m = db.check_files_exist()
    b = not b
    stop_test(b, f'Check move file {b} {m}')
    shutil.move(f + '.back', f)

    # mv folders
    tp.timepoint_id = 'tp3'
    b, m = db.check_folders_exist()
    b = not b
    stop_test(b, f'Check move folders {b} {m}')
    tp.timepoint_id = 'tp2'
    cycle.cycle_id = 'cycle2'
    b, m = db.check_folders_exist()
    b = not b
    stop_test(b, f'Check move folders {b} {m}')
    cycle.cycle_id = 'cycle1'

    # back
    b, m = db.check_folders_exist()
    stop_test(b, f'Check folders {b} {m}')
    b, m = db.check_files_exist()
    stop_test(b, f'Check files {b} {m}')

    # check if metadata are synchronized
    start_test(f"Check metadata sync")
    b, m = db.check_files_metadata()
    stop_test(b, f'Check files metadata {b} {m}')

    # check if metadata are synchronized
    start_test(f"Check metadata sync")
    d = tp.acquisition_datetime
    tp.acquisition_datetime = "1994 06 21"
    b, m = db.check_files_metadata()
    b = not b
    stop_test(b, f'Check files metadata {b} {m}')
    tp.acquisition_datetime = d

    # check if metadata are synchronized
    start_test(f"Check metadata sync")
    roi = tp.rois['spleen']
    roi.name = 'toto'
    b, m = db.check_files_metadata()
    b = not b
    stop_test(b, f'Check files metadata {b} {m}')
    roi.name = 'spleen'

    # check if metadata are synchronized
    start_test(f"Check metadata sync")
    roi1 = tp.rois['spleen']
    roi2 = tp.rois['liver']
    f = roi2.image_file_path
    roi2.image_file_path = roi1.image_file_path
    b, m = db.check_files_metadata()
    b = not b
    stop_test(b, f'Check files metadata {b} {m}')
    roi2.image_file_path = f

    # check if metadata are synchronized
    start_test(f"Check metadata sync")
    im1 = tp.images['ct']
    im2 = tp.images['spect']
    im1.image_file_path = im2.image_file_path
    b, m = db.check_files_metadata()
    b = not b
    stop_test(b, f'Check files metadata {b} {m}')

    # end
    end_tests()
