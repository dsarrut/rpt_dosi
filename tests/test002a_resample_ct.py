#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as im
import rpt_dosi.helpers as he

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test002")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test resample (with gauss)
    # rpt_resample_ct -i data/spect.nii.gz -o data/test001/spect_9mm.nii.gz -s 9
    ct_input = data_folder / "ct_8mm.nii.gz"
    ct_output = output_folder / "ct_tests.nii.gz"
    cmd = f"rpt_resample_ct -i {ct_input} -o {ct_output} -s 9 --sigma auto"
    is_ok = he.run_cmd(cmd, data_folder / "..")

    # compare
    ct_ref = ref_folder / "ct_9mm_ref.nii.gz"
    b = im.test_compare_images(ct_output, ct_ref)
    he.print_tests(b, f"Resample with gauss 001-1 {ct_output} vs {ct_ref}")
    is_ok = b and is_ok

    # test resample (with gauss)
    # rpt_resample_ct -i data/spect.nii.gz -o data/test001/spect_9mm.nii.gz -s 9 --ng
    print()
    cmd = f"rpt_resample_ct -i {ct_input} -o {ct_output} -s 9"
    is_ok = he.run_cmd(cmd, data_folder / "..") and is_ok
    ct_ref = ref_folder / "ct_9mm_ng_ref.nii.gz"

    # compare
    b = im.test_compare_images(ct_output, ct_ref)
    he.print_tests(b, f"Resample with gauss 001-2 {ct_output} vs {ct_ref}")
    is_ok = b and is_ok

    # test resample like
    # rpt_resample_ct -i data/ct_8mm.nii.gz -o data/test001/ct_8.321mm_ref.nii.gz --like data/spect_8.321mm.nii.gz
    print()
    like_input = data_folder / "spect_8.321mm.nii.gz"
    cmd = f"rpt_resample_ct -i {ct_input} -o {ct_output} --like {like_input} --sigma auto"
    is_ok = he.run_cmd(cmd, data_folder / "..") and is_ok

    # compare
    ct_ref = ref_folder / "ct_8.321mm_ref.nii.gz"
    b = im.test_compare_images(ct_output, ct_ref)
    he.print_tests(b, f"Resample with gauss 001-3 {ct_output} vs {ct_ref}")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
