#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import rpt_dosi.utils as he
import rpt_dosi.db as rtpdb
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test003")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # test activity
    start_test('test triexpo')
    # rpt_db_tac_triexpo --db data/activities.json -c cycle1 --no_plot -o data/test003/activities_fit.json
    db_input = data_folder / "activities.json"
    db_output = output_folder / "activities_fit.json"
    cmd = f"rpt_db_tac_triexpo --db {db_input} -o {db_output} -c cycle1 --no_plot"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, 'cmd')

    # compare
    start_test('test triexpo compare')
    db_ref = ref_folder / "activities_fit_ref.json"
    db1 = rtpdb.OLD_db_load(db_output)
    db2 = rtpdb.OLD_db_load(db_ref)
    d1 = db1["cycles"]["cycle1"]["tri_expo_fit"]
    d2 = db2["cycles"]["cycle1"]["tri_expo_fit"]
    print(json.dumps(d1, indent=2))
    b = he.are_dicts_equal(d1, d2, float_tolerance=1e-9)
    stop_test(b, f"Compare tri expo fit")

    # end
    end_tests()
