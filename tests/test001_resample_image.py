#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as im
import rpt_dosi.helpers as he
import os

if __name__ == "__main__":
    # folders
    data_input_folder = he.get_tests_data_folder()
    data_output_folder = he.get_tests_data_folder("test001")
    ct_input = data_input_folder / "ct_8mm.nii.gz"
    is_ok = True
    print(f"Input data folder = {data_input_folder}")
    print(f"Output data folder = {data_output_folder}")

    # test resample (with gauss)
    # rpt_resample_image -i spect.nii.gz -o data/spect_7mm.nii.gz -s 9
    ct_output = data_output_folder / "ct_tests.nii.gz"
    cmd = f"rpt_resample_image -i {ct_input} -o {ct_output} -s 9"
    os.system(cmd)
    ct_ref = data_output_folder / "ct_9mm_ref.nii.gz"
    b = im.test_compare_image_exact(ct_output, ct_ref)
    he.print_tests(b, f"Resample with gauss 001-1 {ct_output}")
    is_ok = b and is_ok

    # test resample (with gauss)
    # rpt_resample_image -i spect.nii.gz -o data/spect_7mm.nii.gz -s 9 --ng
    print()
    cmd = f"rpt_resample_image -i {ct_input} -o {ct_output} -s 9 --ng"
    os.system(cmd)
    ct_ref = data_output_folder / "ct_9mm_ng_ref.nii.gz"
    b = im.test_compare_image_exact(ct_output, ct_ref)
    he.print_tests(b, f"Resample with gauss 001-1 {ct_output}")
    is_ok = b and is_ok

    # test resample like
    # rpt_resample_image -i data/ct_8mm.nii.gz -o data/ct_8.321mm_ref.nii.gz --like data/spect_8.321mm.nii.gz
    print()
    like_input = data_input_folder / "spect_8.321mm.nii.gz"
    cmd = (
        f"rpt_resample_image -i {ct_input} -o {ct_output} --like {like_input} -d -1000"
    )
    os.system(cmd)
    ct_ref = data_output_folder / "ct_8.321mm_ref.nii.gz"
    b = im.test_compare_image_exact(ct_output, ct_ref)
    he.print_tests(b, f"Resample with gauss 001-1 {ct_output}")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
