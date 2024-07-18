#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.db as rtpdb

# rpt_db_set_spect_datetime_from_dicom --db db.json -o db_datetime.json
# rpt_db_spect_calibration --db db.json -o db_calib.json -c 0.176906614

if __name__ == "__main__":
    # folders
    _, ref_folder, output_folder = he.get_tests_folders("test007")
    data_folder = ref_folder
    ref_folder = ref_folder / "ref_json"
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test 1
    # rpt_db_add_rois --db db.json -n Images_IEC -l rois.json -o db_roi.json
    print("rpt_db_add_rois")
    db_input = data_folder / "db.json"
    db_output = output_folder / "db_roi.json"
    rois_json = data_folder / "rois.json"
    db_ref = ref_folder / "db_roi.json"
    cmd = f"rpt_db_add_rois --db {db_input} -n Images_IEC -l {rois_json} -o {db_output}"
    is_ok = he.run_cmd(cmd, data_folder)

    # compare
    db1 = rtpdb.OLD_db_load(db_output)
    db2 = rtpdb.OLD_db_load(db_ref)
    b = he.are_dicts_float_equal(db1, db2)
    he.print_tests(b, f"Compare JSON {db_output} vs {db_ref}")
    is_ok = b and is_ok

    # test 2
    # rpt_db_set_spect_datetime_from_dicom --db db.json -o db_datetime.json
    print("rpt_db_set_spect_datetime_from_dicom")
    db_input = data_folder / "db.json"
    db_output = output_folder / "db_datetime.json"
    db_ref = ref_folder / "db_datetime.json"
    cmd = f"rpt_db_set_spect_datetime_from_dicom --db {db_input} -o {db_output}"
    cmd_ok = he.run_cmd(cmd, data_folder)

    # compare
    db1 = rtpdb.OLD_db_load(db_output)
    db2 = rtpdb.OLD_db_load(db_ref)
    b = he.are_dicts_float_equal(db1, db2) and cmd_ok
    he.print_tests(b, f"Compare JSON {db_output} vs {db_ref}")
    is_ok = b and is_ok

    # test 3
    # rpt_db_spect_calibration --db db.json -o db_calib.json -c 0.176906614
    print("rpt_db_spect_calibration")
    db_input = data_folder / "db.json"
    db_output = output_folder / "db_calib.json"
    db_ref = ref_folder / "db_calib.json"
    s = 1 / 0.176906614
    cmd = f"rpt_db_spect_calibration --db {db_input} -c 0.176906614 -o {db_output}"
    cmd_ok = he.run_cmd(cmd, data_folder)

    # compare
    db1 = rtpdb.OLD_db_load(db_output)
    db2 = rtpdb.OLD_db_load(db_ref)
    b = he.are_dicts_float_equal(db1, db2) and cmd_ok
    he.print_tests(b, f"Compare JSON {db_output} vs {db_ref}")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
