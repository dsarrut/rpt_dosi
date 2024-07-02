#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import rpt_dosi.utils as he
import rpt_dosi.db as rdb
import copy
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test007b")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # create a db from scratch
    start_test(f"Create a new database with cycle and TP")
    db_file_path = output_folder / "db007b.json"
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
    db = rdb.PatientTreatmentDatabase(db_file_path, create=True)
    cycle = rdb.CycleTreatmentDatabase(db, "cycle1")
    db.add_cycle(cycle)
    tp = cycle.add_new_timepoint("tp1")

    # add images
    tp.add_image_from_file("ct",
                           data_folder / "ct_8mm.nii.gz",
                           image_type="CT",
                           filename="ct1.nii.gz",
                           mode="copy",
                           exist_ok=True)
    im = tp.add_image_from_file("spect",
                                data_folder / "spect_8.321mm.nii.gz",
                                image_type="SPECT",
                                filename="spect.nii.gz",
                                mode="copy",
                                unit='Bq',
                                exist_ok=True)
    print(im.image_file_path)
    tp.add_image_from_file("spect2",  # this one has a json, not need for unit
                           data_folder / "spect_10mm_with_json.nii.gz",
                           image_type="SPECT",
                           filename="spect2.nii.gz",
                           mode="copy",
                           exist_ok=True)
    tp.add_image_from_file("pet",
                           data_folder / "ct_8mm.nii.gz",
                           image_type="PET",
                           filename="pet.nii.gz",
                           unit='Bq/mL',
                           mode="copy",
                           exist_ok=True)

    print(tp)
    print(tp.info())
    print()
    for image in tp.images.values():
        print('-> ', image)
        print(image.info() + '\n')

    # try to set the same image twice
    try:
        # same image name
        tp.add_image_from_file("ct", data_folder / "ct_8mm.nii.gz", filename="ct.nii.gz", mode="copy")
        b = False
    except he.Rpt_Error as e:
        b = True
    stop_test(b, f"I cannot set the image two times: {b}")

    # try to set a wrong image type
    try:
        # same image name
        tp.add_image_from_file("fake",  # this one has a json, not need for unit
                               data_folder / "spect_10mm_with_json.nii.gz",
                               image_type="CT",
                               filename="toto.nii.gz",
                               mode="copy",
                               exist_ok=True)
        b = False
    except:
        b = True
    stop_test(b, f"Can I set a spect to a CT ? {b}")

    # test
    start_test(f"check DB body weight update when add image")
    db.body_weight_kg = 666
    tp.add_image_from_file("ct_bw",
                           tp.images["ct"].image_file_path,
                           image_type="CT",
                           filename="ct1.nii.gz",
                           mode="dry_run",
                           exist_ok=True)
    print(tp.images["ct_bw"].info())
    tp.sync_metadata_image("ct_bw", sync_policy='db_to_image')
    b = tp.images["ct_bw"].body_weight_kg == db.body_weight_kg == 666
    stop_test(b, f"Check body weight db and image 666 {b}")

    # test
    start_test(f"check body weight IMAGE update + sync")
    db.body_weight_kg = None
    tp.images["ct_bw"].body_weight_kg = 333
    print(f'db = {db.body_weight_kg} and im = {tp.images["ct_bw"].body_weight_kg}')
    tp.sync_metadata_image("ct_bw")
    print(f'db = {db.body_weight_kg} and im = {tp.images["ct_bw"].body_weight_kg}')
    b = tp.images["ct_bw"].body_weight_kg == db.body_weight_kg == 333
    stop_test(b, "Check body weight db and image")

    # test
    start_test(f"modify both + sync")
    db.body_weight_kg = 111
    tp.images["ct_bw"].body_weight_kg = 222
    print(f'db = {db.body_weight_kg} and im = {tp.images["ct_bw"].body_weight_kg}')
    db.sync_metadata_images()
    print(f'db = {db.body_weight_kg} and im = {tp.images["ct_bw"].body_weight_kg}')
    b = tp.images["ct_bw"].body_weight_kg == 222 and db.body_weight_kg == 111
    stop_test(b, "Check body weight db and image")

    # test
    start_test(f"modify both + sync")
    db.body_weight_kg = 111
    tp.images["ct_bw"].body_weight_kg = 222
    print(f'db = {db.body_weight_kg} and im = {tp.images["ct_bw"].body_weight_kg}')
    db.sync_metadata_images(sync_policy="db_to_image")
    print(f'db = {db.body_weight_kg} and im = {tp.images["ct_bw"].body_weight_kg}')
    b = tp.images["ct_bw"].body_weight_kg and db.body_weight_kg == 111
    stop_test(b, "Check body weight db and image")

    # test
    start_test(f"modify DB + sync")
    db.body_weight_kg = 222
    tp.images["ct_bw"].body_weight_kg = None
    print(f'db = {db.body_weight_kg} and im = {tp.images["ct_bw"].body_weight_kg}')
    tp.sync_metadata_image("ct_bw")
    print(f'db = {db.body_weight_kg} and im = {tp.images["ct_bw"].body_weight_kg}')
    b = tp.images["ct_bw"].body_weight_kg == db.body_weight_kg == 222
    stop_test(b, "Check body weight db and image")

    # check
    start_test(f"check DB from-to dict")
    d1 = copy.deepcopy(db.to_dict())
    db.from_dict(d1)
    d2 = copy.deepcopy(db.to_dict())
    b = he.are_dicts_equal(d1, d2)
    stop_test(b, f"Compare the from_dict to_dict {b}")

    # write and check
    start_test(f"check DB write read")
    im = db['cycle1']['tp1'].images['spect']
    im.body_weight_kg = 999
    print(im.info())
    db.sync_metadata_images(sync_policy="db_to_image")
    db.write()
    print('write done')
    # db2 = rdb.PatientTreatmentDatabase(ref_folder / "db007b.json")
    db2 = rdb.PatientTreatmentDatabase(output_folder / "db007b.json")
    b = he.are_dicts_equal(db.to_dict(), db2.to_dict())
    stop_test(b, f"Compare write and read: {b}")

    # date
    start_test(f"check dates I")
    im = db['cycle1']['tp1'].images['spect']
    im.injection_datetime = "2050 01 01"
    db['cycle1'].injection_datetime = "2000 01 01"
    db['cycle1']['tp1'].sync_metadata_image("spect", sync_policy="db_to_image")
    im.acquisition_datetime = None
    im.time_from_injection_h = 24.5
    b = im.acquisition_datetime == "2000-01-02 00:30:00" and im.time_from_injection_h == 24.5
    stop_test(b, f"Check dates: {im}")

    # check
    start_test(f"check dates II")
    im = db['cycle1']['tp1'].images['spect']
    db['cycle1'].injection_datetime = "2000 01 01"
    im.injection_datetime = "2050 01 01"
    db['cycle1']['tp1'].sync_metadata_image("spect", sync_policy="image_to_db")
    print(im)
    im.acquisition_datetime = None
    im.time_from_injection_h = 24.5
    print(im)
    b = im.acquisition_datetime == "2050-01-02 00:30:00" and im.time_from_injection_h == 24.5
    stop_test(b, f"Check dates: {im}")

    # check
    start_test(f"check dates III")
    im = db['cycle1']['tp1'].images['spect']
    im.acquisition_datetime = "2099 01 01"
    im.injection_datetime = None
    print(im)
    im.time_from_injection_h = 24.5
    print(im)
    b = im.injection_datetime == "2098-12-30 23:30:00" and im.time_from_injection_h == 24.5
    stop_test(b, f"Check dates: {im}")

    # check
    start_test(f"check dates IV")
    im = db['cycle1']['tp1'].images['spect']
    im.acquisition_datetime = "2099 01 01"
    im.injection_datetime = "2029 01 01"
    print(im)
    try:
        im.time_from_injection_h = 24.5
        b = False
    except:
        b = True
    print(im)
    stop_test(b, f"Check dates: {im}")

    # end
    end_tests()
