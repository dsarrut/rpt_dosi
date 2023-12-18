#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as im
import rpt_dosi.helpers as he
import os

if __name__ == "__main__":
    # folders
    data_input_folder = he.get_tests_data_folder()
    data_output_folder = he.get_tests_data_folder("test002")
    is_ok = True
    print(f"Input data folder = {data_input_folder}")
    print(f"Output data folder = {data_output_folder}")

    # test activity
    # rpt_spect_calibration -i spect_8.321mm.nii.gz -o test002/spect_activity_ref.nii.gz -c 0.66
    spect_input = data_input_folder / "spect_8.321mm.nii.gz"
    spect_output = data_output_folder / "spect_activity.nii.gz"
    cmd = f"rpt_spect_calibration -i {spect_input} -o {spect_output} -c 0.666"
    print(cmd)
    os.system(cmd)
    spect_ref = data_output_folder / "spect_activity_ref.nii.gz"
    b = im.test_compare_image_exact(spect_output, spect_ref)
    he.print_tests(b, f"SPECT calibration activity")
    is_ok = b and is_ok

    # test activity concentration
    # rpt_spect_calibration -i spect_8.321mm.nii.gz -o test002/spect_activity_conc_ref.nii.gz -c 0.66 --concentration
    spect_input = data_input_folder / "spect_8.321mm.nii.gz"
    spect_output = data_output_folder / "spect_activity_conc.nii.gz"
    cmd = f"rpt_spect_calibration -i {spect_input} -o {spect_output} -c 0.222 --concentration"
    print(cmd)
    os.system(cmd)
    spect_ref = data_output_folder / "spect_activity_conc_ref.nii.gz"
    b = im.test_compare_image_exact(spect_output, spect_ref)
    he.print_tests(b, f"SPECT calibration activity")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
