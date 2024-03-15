#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as im
import rpt_dosi.helpers as he
import SimpleITK as sitk
import numpy as np

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test resample
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_test.nii.gz"
    cmd = f"rpt_resample_spect -i {spect_input} -o {spect_output} -s 12 --unit Bq --sigma auto"
    is_ok = he.run_cmd(cmd, data_folder / "..")

    # compare
    spect_ref = ref_folder / "spect_12mm_ref.nii.gz"
    b = im.compare_images(spect_output, spect_ref)
    he.print_tests(b, f"Resample with bq {spect_output} vs {spect_ref}")
    is_ok = b and is_ok

    # check total counts
    spect1 = sitk.GetArrayViewFromImage(sitk.ReadImage(spect_input))
    tc_input = np.sum(spect1)
    spect2 = sitk.GetArrayViewFromImage(sitk.ReadImage(spect_output))
    tc_output = np.sum(spect2)
    diff = np.fabs(tc_input - tc_output) / tc_input * 100
    b = diff < 0.5
    he.print_tests(b, f'Total counts = {tc_input}, {tc_output}  => {diff} %')
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
