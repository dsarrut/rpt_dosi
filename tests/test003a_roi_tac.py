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
    ref_activities = {'liver': [257.41958597653644, 76.87083050272122, 8.713141811687267],
                      'spleen': [19.377683177487604, 6.74894709364374, 1.1591803949505457],
                      'left_kidney': [112.16342482399277, 75.6176254208148, 8.51152515600019]}

    b, msg = ru.compare_dict(ref_times, times)
    stop_test(b, f'Compare times: {msg}')
    b, msg = ru.compare_dict(ref_activities, activities)
    stop_test(b, f'Compare activities: {msg}')

    # end
    end_tests()
