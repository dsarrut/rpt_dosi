#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as ru
import rpt_dosi.db as rdb
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = ru.get_tests_folders("test003")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")

    # open the db
    db = rdb.PatientTreatmentDatabase(data_folder / "p12_10.0mm" / "db.json")
    print(db)

    # test API
    start_test('test tac extraction')
    cycle = db.get_cycle("cycle1")
    roi_names = ("liver", "spleen", "left_kidney")
    spect_name = "spect"
    times, activities = rdb.compute_time_activity_curve(cycle, roi_names, spect_name)
    print(times, activities)

    # compare
    ref_times = {'liver': [4.528888888888889, 24.737222222222222, 117.81472222222222],
                 'spleen': [4.528888888888889, 24.737222222222222, 117.81472222222222],
                 'left_kidney': [4.528888888888889, 24.737222222222222, 117.81472222222222]}
    ref_activities = {'liver': [3059.0058518312558, 913.4826296039937, 103.5412736056337],
                      'spleen': [230.27170174310402, 80.20006959492939, 13.774940973280579],
                      'left_kidney': [1332.8767173564536, 898.5903605135633, 101.14539326000637]}

    b, msg = ru.compare_dict(ref_times, times)
    stop_test(b, f'Compare times: {msg}')
    b, msg = ru.compare_dict(ref_activities, activities)
    stop_test(b, f'Compare activities: {msg}')

    # end
    end_tests()
