#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import rpt_dosi.helpers as he
import rpt_dosi.db as rtpdb
import os

if __name__ == "__main__":
    # folders
    data_input_folder = he.get_tests_data_folder()
    data_output_folder = he.get_tests_data_folder("test003")
    is_ok = True
    print(f"Input data folder = {data_input_folder}")
    print(f"Output data folder = {data_output_folder}")

    # test activity
    # rpt_db_tac_triexpo --db activities.json -c cycle1 --no_plot -o activities_fit.json
    db_input = data_input_folder / "activities.json"
    db_output = data_output_folder / "activities_fit.json"
    cmd = f"rpt_db_tac_triexpo --db {db_input} -o {db_output} -c cycle1 --no_plot"
    print(cmd)
    os.system(cmd)
    db_ref = data_output_folder / "activities_fit_ref.json"

    # compare
    db1 = rtpdb.db_load(db_output)
    db2 = rtpdb.db_load(db_ref)
    d1 = db1["cycles"]["cycle1"]["tri_expo_fit"]
    d2 = db2["cycles"]["cycle1"]["tri_expo_fit"]
    print(json.dumps(d1, indent=2))
    b = d1 == d2
    he.print_tests(b, f"Compare tri expo fit")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
