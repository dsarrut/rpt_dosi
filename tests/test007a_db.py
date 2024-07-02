#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import rpt_dosi.utils as he
import rpt_dosi.db as rdb
import json
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test007a")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # create a db from scratch
    start_test(f"Create a new database")
    db_filepath = output_folder / "db007a.json"
    if os.path.exists(db_filepath):
        os.remove(db_filepath)
    db = rdb.PatientTreatmentDatabase(db_filepath, create=True)

    # modify metadata
    db.patient_id = "p1"
    db.body_weight_kg = 123

    # add a cycle
    cycle = rdb.CycleTreatmentDatabase(db, "cycle1")
    cycle.injection_activity_mbq = 666
    cycle.injection_datetime = "2022-08-09"
    db.add_cycle(cycle)

    # add a cycle with same id
    try:
        db.add_cycle(cycle)
        b = False
    except:
        b = True
    stop_test(b, "OK, I cannot add two times the same cycle_id")

    # add another cycle
    c2 = db.add_new_cycle("cycle2")
    c2.add_new_timepoint("tp1")
    c2.add_new_timepoint("tp2")
    c2.injection_activity_mbq = 777.7
    tp = rdb.TimepointTreatmentDatabase(cycle, "tp3")
    try:
        c2.add_timepoint(tp)
        b = False
    except:
        b = True
    stop_test(b, "OK, I cannot add wrong timepoint")
    cycle.add_timepoint(tp)

    # write, print and check
    start_test('write and read db')
    db.write()
    print(f'db ->', db)
    print(db.info())
    print()
    start_test('Compare to reference json')
    db_ref_filepath = ref_folder / "db007a_ref.json"
    db_ref = json.load(open(db_ref_filepath))
    b = he.are_dicts_equal(db_ref, db.to_dict())
    he.print_tests(b, f'Compare the db {db_filepath} and {db_ref_filepath}')

    # read an existing db
    start_test('Read an existing db')
    db2 = rdb.PatientTreatmentDatabase(db_filepath)
    b = db.patient_id == db2.patient_id
    b = db.body_weight_kg == db2.body_weight_kg and b
    b = db.check_folders_exist() and b
    b = db2.check_folders_exist() and b
    stop_test(b, f'Compare write/read db {db_filepath}')

    # update a db
    start_test('Update a db')
    db3 = rdb.PatientTreatmentDatabase(db_filepath)
    db3.patient_id = "toto"
    db3.body_weight_kg = 321.0
    db3.add_new_cycle("cycle3")
    db3.remove_cycle("cycle1")
    db3.write(output_folder / "db007_db3.json")
    print(db3)
    print(db3.db_file_path)
    db4 = rdb.PatientTreatmentDatabase(output_folder / "db007_db3.json")
    b = he.are_dicts_equal(db4.to_dict(), db3.to_dict())
    stop_test(b, f'Compare updated db')

    # end
    end_tests()
