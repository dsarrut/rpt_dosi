#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import rpt_dosi.helpers as he
import rpt_dosi.db as rdb
import copy

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test007")
    ref_folder = ref_folder / "ref_json"
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()
    is_ok = True

    # create a db from scratch
    print()
    he.warning(f"Create a new database with cycle and TP")
    db_filepath = output_folder / "db007b.json"
    if os.path.exists(db_filepath):
        os.remove(db_filepath)
    db = rdb.PatientTreatmentDatabase(db_filepath, create=True)
    cycle = rdb.TreatmentCycle(db, "cycle1")
    db.add_cycle(cycle)
    tp = cycle.add_new_timepoint("tp1")

    # add images
    tp.add_image("ct",
                 data_folder / "ct_8mm.nii.gz",
                 image_type="CT",
                 filename="ct1.nii.gz",
                 mode="copy",
                 exist_ok=True)
    tp.add_image("spect",
                 data_folder / "spect_8.321mm.nii.gz",
                 image_type="SPECT",
                 filename="spect.nii.gz",
                 mode="copy",
                 unit='Bq',
                 exist_ok=True)
    tp.add_image("spect2",  # this one has a json, not need for unit
                 data_folder / "spect_10mm_with_json.nii.gz",
                 image_type="SPECT",
                 filename="spect2.nii.gz",
                 mode="copy",
                 exist_ok=True)
    tp.add_image("pet",  # this one has a json, not need for unit
                 data_folder / "spect_10mm_with_json.nii.gz",
                 image_type="PET",
                 filename="pet.nii.gz",
                 mode="copy",
                 exist_ok=True)

    # try to set the same image twice
    try:
        # same image name
        tp.add_image("ct", data_folder / "ct_8mm.nii.gz", filename="ct.nii.gz", mode="copy")
        is_ok = False
    except:
        he.print_tests(is_ok, "OK, I cannot set the image two times")

    # try to set the same image twice
    try:
        # same image name
        tp.add_image("fake",  # this one has a json, not need for unit
                     data_folder / "spect_10mm_with_json.nii.gz",
                     image_type="CT",
                     filename="toto.nii.gz",
                     mode="copy",
                     exist_ok=True)
        is_ok = False
    except:
        he.print_tests(is_ok, "OK, I cannot set the unit of a spect to a CT")

    tp.add_roi("liver",
               data_folder / "rois" / "liver.nii.gz",
               mode="copy",
               exist_ok=True)

    # check
    print()
    he.warning(f"check DB from to dict")
    d1 = copy.deepcopy(db.to_dict())
    db.from_dict(d1)
    d2 = copy.deepcopy(db.to_dict())
    is_ok = he.are_dicts_equal(d1, d2) and is_ok
    he.print_tests(is_ok, "Compare the from_dict to_dict")

    # write and check
    print()
    he.warning(f"check DB write read")
    db.write()
    db2 = rdb.PatientTreatmentDatabase(ref_folder / "db007b.json")
    is_ok = he.are_dicts_equal(db.to_dict(), db2.to_dict()) and is_ok
    he.print_tests(is_ok, "Compare write and read")

    # end
    he.test_ok(is_ok)
