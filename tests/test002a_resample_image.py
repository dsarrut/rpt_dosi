#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as he
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test002")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # test ct + gauss
    start_test('resample ct with gauss')
    ct_input = data_folder / "ct_8mm.nii.gz"
    ct_output = output_folder / "ct_tests.nii.gz"
    ct_ref = ref_folder / "ct_9mm_ref.nii.gz"
    ct = rim.read_ct(ct_input)
    print(ct)
    resampled_ct = rim.resample_ct_spacing(ct, [9, 9, 9], gaussian_sigma="auto")
    resampled_ct.write(ct_output)
    print(ct)
    b = rim.test_compare_images(ct_output, ct_ref)
    stop_test(b, f"Resample ct with gauss {ct_output} vs {ct_ref}")

    # test ct no gauss
    start_test('resample ct wo gauss')
    ct_ref = ref_folder / "ct_9mm_ng_ref.nii.gz"
    ct = rim.read_ct(ct_input)
    print(ct)
    resampled_ct = rim.resample_ct_spacing(ct, [9, 9, 9], gaussian_sigma=None)
    resampled_ct.write(ct_output)
    print(ct)
    b = rim.test_compare_images(ct_output, ct_ref)
    stop_test(b, f"Resample ct without gauss {ct_output} vs {ct_ref}")

    # test ct like
    start_test('resample ct like')
    ct_ref = ref_folder / "ct_8.321mm_ref.nii.gz"
    like_input = data_folder / "spect_8.321mm.nii.gz"
    ct = rim.read_ct(ct_input)
    print(ct.info())
    like = rim.read_ct(like_input)
    print(like.info())
    resampled_ct = rim.resample_ct_like(ct, like, gaussian_sigma="auto")
    resampled_ct.write(ct_output)
    print(ct)
    b = rim.test_compare_images(ct_output, ct_ref)
    stop_test(b, f"Resample ct like:  {ct_output} vs {ct_ref}")

    # end
    end_tests()
