#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as he
import json

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test011")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test
    print(f'set metadata Bq, SPECT and scaling')
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    roi_filename = data_folder / "rois" / "liver.nii.gz"
    ct_filename = data_folder / "ct_8mm.nii.gz"
    res_json = output_folder / "spect_roi_statistics.json"
    cmd = f"rpt_spect_roi_statistics -s {spect_input} -r {roi_filename} -u Bq -o {res_json}"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")

    # read json
    with open(res_json, "r") as f:
        res = json.load(f)
    ref_res = {'mean': 16627.84375, 'std': 12616.0859375, 'min': -17.069276809692383,
               'max': 76888.78125, 'sum': 29880236.0, 'volume_cc': 1035.3201311307996}
    is_ok = he.are_dicts_float_equal(ref_res, res) and cmd_ok
    he.print_tests(is_ok, f"stats {res}")

    # from API
    spect = rim.read_spect(spect_input, 'Bq')
    roi = rim.read_roi(roi_filename, "unnamed_roi")
    ct = rim.read_ct(ct_filename)
    res = rim.image_roi_stats(roi, spect, ct, "spect")
    ref_res['mass_g'] = 1089.0692347997906
    is_ok = he.are_dicts_float_equal(ref_res, res) and is_ok
    he.print_tests(is_ok, f"stats {res}")

    # end
    he.test_ok(is_ok)
