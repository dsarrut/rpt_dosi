#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import rpt_dosi.helpers as he
import rpt_dosi.db as rdb
import copy

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test007c")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()
    ok = True

    # create a db from scratch
    print()
    he.warning(f"Create a new database with cycle and TP")
    db_filepath = output_folder / "db007c.json"
    if os.path.exists(db_filepath):
        os.remove(db_filepath)
    db = rdb.PatientTreatmentDatabase(db_filepath, create=True)
    cycle = rdb.CycleTreatmentDatabase(db, "cycle1")
    db.add_cycle(cycle)
    tp = cycle.add_new_timepoint("tp1")

    # add
    tp.add_roi_from_file("liver",
                         data_folder / "rois" / "liver.nii.gz",
                         mode="copy",
                         exist_ok=True)
    tp.add_roi_from_file("left kidney",
                         data_folder / "rois" / "kidney_left.nii.gz",
                         mode="copy",
                         exist_ok=True)
    print(tp)

    # try to set the same image twice
    try:
        # same image name
        tp.add_roi_from_file("liver", data_folder / "ct_8mm.nii.gz")
        ok = False
    except:
        he.print_tests(ok, "I cannot set the ROI two times")

    # try to set wrong extension
    try:
        # same image name
        tp.add_image_from_file("ct",  # this one has a json, not need for unit
                               data_folder / "spect_10mm_with_json.nii.gz",
                               filename="toto.mhd")
        ok = False
    except:
        ok = he.print_tests(ok, "I cannot set a wrong extension") and ok

    # check
    print()
    he.warning(f"check DB from to dict")
    d1 = copy.deepcopy(db.to_dict())
    db.from_dict(d1)
    d2 = copy.deepcopy(db.to_dict())
    ok = he.are_dicts_equal(d1, d2) and ok
    he.print_tests(ok, "Compare the from_dict to_dict")

    # write and check
    print()
    he.warning(f"check DB write read")
    db.write()
    print(db.db_file_path)
    db2 = rdb.PatientTreatmentDatabase(ref_folder / "db007c.json")
    print(db2.db_file_path)
    ok = he.are_dicts_equal(db.to_dict(), db2.to_dict()) and ok
    he.print_tests(ok, "Compare write and read")

    # several rois
    print()
    he.warning(f"several rois")
    tp = db['cycle1']['tp1']
    tp.rois.pop('liver')
    roi_list = [
        {'roi_id': 'colon', 'filename': data_folder / 'rois' / 'colon.nii.gz'},
        {'roi_id': 'skull', 'filename': data_folder / 'rois' / 'skull.nii.gz'},
        {'roi_id': 'liver', 'filename': data_folder / 'rois' / 'colon.nii.gz'},
        {'roi_id': 'spleen', 'filename': data_folder / 'rois' / 'colon.nii.gz'},
    ]
    tp.add_rois(roi_list, exist_ok=True)
    print(tp)
    print(db.get_cycle('cycle1').get_timepoint('tp1'))
    print(tp.info())
    b = len(tp.rois) == 5 and 'liver' in tp.rois and 'spleen' in tp.rois
    ok = he.print_tests(b, "Check if 5 rois") and ok

    # end
    he.test_ok(ok)
