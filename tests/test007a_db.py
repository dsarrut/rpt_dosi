#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import rpt_dosi.helpers as he
import rpt_dosi.db as rdb
import json

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
    print(f"Create a new database")
    db_filepath = output_folder / "db007.json"
    if os.path.exists(db_filepath):
        os.remove(db_filepath)
    db = rdb.PatientTreatmentDatabase(db_filepath, create=True)

    # modify metadata
    db.patient_id = "p1"
    db.body_weight_kg = 123

    # add a cycle
    cycle = rdb.TreatmentCycle(db, "cycle1")
    db.add_cycle(cycle)

    # add a cycle with same id
    try:
        db.add_cycle(cycle)
        is_ok = False
    except:
        he.print_tests(is_ok, "OK, I cannot add two times the same cycle_id")

    # add another cycle
    c2 = db.add_new_cycle("cycle2")
    c2.add_new_timepoint("tp1")
    c2.add_new_timepoint("tp2")
    tp = rdb.ImagingTimepoint(cycle, "tp3")
    try:
        c2.add_timepoint(tp)
        is_ok = False
    except:
        he.print_tests(is_ok, "OK, I cannot add wrong timepoint")
    cycle.add_timepoint(tp)
    tp.ct_image_filename = "toto.mhd"
    tp.spect_image_filename = "titi.mhd"

    # write, print and check
    db.write()
    print(db)
    print(db.info())
    db_ref_filepath = output_folder / "db007.json"
    db_ref = json.load(open(db_ref_filepath))
    b = he.are_dicts_equal(db_ref, db.to_dict())
    he.print_tests(b, f'Compare the db {db_filepath} and {db_ref_filepath}')
    is_ok = b and is_ok
    print()

    # read an existing db
    print('Read an existing db')
    db2 = rdb.PatientTreatmentDatabase(db_filepath)
    is_ok = db.patient_id == db2.patient_id and is_ok
    is_ok = db.body_weight_kg == db2.body_weight_kg and is_ok
    is_ok = db.check_folders() and is_ok
    is_ok = db2.check_folders() and is_ok
    he.print_tests(is_ok, f'Compare write/read db {db_filepath}')
    print()

    # update a db
    print('Update a db')
    db3 = rdb.PatientTreatmentDatabase(db_filepath)
    db3.patient_id = "toto"
    db3.body_weight_kg = 321.0
    db3.add_new_cycle("cycle3")
    db3.remove_cycle("cycle1")
    db3.write(output_folder / "db007_db3.json")
    print(db3)
    db4 = rdb.PatientTreatmentDatabase(output_folder / "db007_db3.json")
    is_ok = he.are_dicts_equal(db4.to_dict(), db3.to_dict()) and is_ok
    he.print_tests(is_ok, f'Compare updated db')

    # end
    he.test_ok(is_ok)
