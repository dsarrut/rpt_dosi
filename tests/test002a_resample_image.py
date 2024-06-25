#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.helpers as he
from rpt_dosi.helpers import warning

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test002")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()
    is_ok = True

    # test ct + gauss
    print()
    warning('resample ct with gauss')
    ct_input = data_folder / "ct_8mm.nii.gz"
    ct_output = output_folder / "ct_tests.nii.gz"
    ct_ref = ref_folder / "ct_9mm_ref.nii.gz"
    ct = rim.read_ct(ct_input)
    print(ct)
    resampled_ct = rim.resample_ct_spacing(ct, [9, 9, 9], gaussian_sigma="auto")
    resampled_ct.write(ct_output)
    print(ct)
    b = rim.test_compare_images(ct_output, ct_ref)
    is_ok = he.print_tests(b, f"Resample ct with gauss {ct_output} vs {ct_ref}") and is_ok

    # test ct no gauss
    print()
    warning('resample ct wo gauss')
    ct_ref = ref_folder / "ct_9mm_ng_ref.nii.gz"
    ct = rim.read_ct(ct_input)
    print(ct)
    resampled_ct = rim.resample_ct_spacing(ct, [9, 9, 9], gaussian_sigma=None)
    resampled_ct.write(ct_output)
    print(ct)
    b = rim.test_compare_images(ct_output, ct_ref)
    is_ok = he.print_tests(b, f"Resample ct without gauss {ct_output} vs {ct_ref}") and is_ok

    # test ct like
    print()
    warning('resample ct like')
    ct_ref = ref_folder / "ct_8.321mm_ref.nii.gz"
    like_input = data_folder / "spect_8.321mm.nii.gz"
    ct = rim.read_ct(ct_input)
    print(ct)
    like = rim.read_ct(like_input)
    print(like)
    resampled_ct = rim.resample_ct_like(ct, like, gaussian_sigma="auto")
    resampled_ct.write(ct_output)
    print(ct)
    b = rim.test_compare_images(ct_output, ct_ref)
    is_ok = he.print_tests(b, f"Resample ct like:  {ct_output} vs {ct_ref}") and is_ok

    # end
    he.test_ok(is_ok)
