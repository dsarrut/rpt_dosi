#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

import rpt_dosi.utils as he
import rpt_dosi.db as rdb
import rpt_dosi.dosimetry as dosi
from rpt_dosi.utils import start_test, stop_test, end_tests
import numpy as np
import radioactivedecay as rd

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test003")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # read db
    db = rdb.PatientTreatmentDatabase(data_folder / "p12_10.0mm" / "db.json")
    print(db)

    # decay
    rad = "Lu177"
    isotope = rd.Nuclide(rad)
    half_life_h = isotope.half_life("h")
    print(f"Radionuclide half life {rad} = {half_life_h:.2f} h")
    decay_constant = np.log(2) / half_life_h

    # ref data
    ref = {'liver': {'A1': -6695.913082140688, 'k1': -1.3, 'A2': 5066.583106081936, 'k2': -0.25107284770960764,
                     'A3': 1629.3299760587513, 'k3': -0.019047282810862775},
           'spleen': {'A1': -469.501168695041, 'k1': -1.3, 'A2': 341.4122648970194, 'k2': -0.24037677154419718,
                      'A3': 128.08890379802162, 'k3': -0.014581963740819421},
           'left_kidney': {'A1': -1410.8404548674637, 'k1': -1.3, 'A2': -194.9005196294733, 'k2': -0.12003567898580024,
                           'A3': 1605.740974496937, 'k3': -0.01912221178950807}}

    # test API
    cycle = db.get_cycle("cycle1")
    roi_names = ("liver", "spleen", "left_kidney")
    spect_name = "spect"
    times, activities = rdb.compute_time_activity_curve(cycle, roi_names, spect_name)
    for roi_name in roi_names:
        start_test(f'test API tri expo {roi_name}')
        t = np.array(times[roi_name])
        a = np.array(activities[roi_name])
        a = dosi.decay_corrected_tac(t, a, decay_constant)
        r = dosi.triexpo_fit(t, a)
        print(r)
        b = he.are_dicts_float_equal(r, ref[roi_name], float_tolerance=1e6)
        stop_test(b, f'Compare dic')

    # test cmd line
    start_test(f'test cmd line tri expo')
    db_input = data_folder / "p12_10.0mm" / "db.json"
    output_file = output_folder / "activities_fit.json"
    cmd = f"rpt_db_tac_triexpo --db {db_input} -o {output_file} -c cycle1 --no_plot"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, 'cmd')

    # compare
    ref = ref_folder / "activities_fit_ref.json"
    ref_data = json.load(ref.open())
    data = json.load(output_file.open())
    for k in ref_data.keys():
        start_test(f'test triexpo compare {k}')
        ref_data[k].pop('times')
        ref_data[k].pop('activities')
        data[k].pop('times')
        data[k].pop('activities')
        b = he.are_dicts_float_equal(ref_data[k], data[k], float_tolerance=1e6)
        stop_test(b, f"Compare tri expo fit")

    # test cmd line
    start_test(f'test cmd line tri expo one single roi')
    output_file = output_folder / "activities_fit_2.json"
    cmd = f"rpt_db_tac_triexpo --db {db_input} -o {output_file} -c cycle1 -r liver --no_plot"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, 'cmd')

    # compare
    ref = ref_folder / "activities_fit_ref.json"
    ref_data = json.load(ref.open())
    data = json.load(output_file.open())
    for k in data.keys():
        start_test(f'test triexpo compare {k}')
        ref_data[k].pop('times')
        ref_data[k].pop('activities')
        data[k].pop('times')
        data[k].pop('activities')
        b = he.are_dicts_float_equal(ref_data[k], data[k], float_tolerance=1e6)
        stop_test(b, f"Compare tri expo fit")
    # end
    end_tests()
