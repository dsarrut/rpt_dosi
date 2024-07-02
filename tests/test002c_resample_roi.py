#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as im
import rpt_dosi.utils as he
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test002")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test resample (with gauss)
    # rpt_resample_roi -i data/roi.nii.gz -o data/test001/roi_9mm.nii.gz -s 9
    start_test('cmd line resample')
    roi_input = data_folder / "rois" / "liver.nii.gz"
    roi_output = output_folder / "roi_test.nii.gz"
    cmd = f"rpt_resample_roi -i {roi_input} -o {roi_output} -s 7.5"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, 'cmd line resample')

    # compare
    start_test('compare with ref')
    roi_ref = ref_folder / "liver_7.5mm_ref.nii.gz"
    b = im.test_compare_images(roi_output, roi_ref)
    stop_test(b, f"Resample ROI {roi_output} vs {roi_ref}")

    # end
    end_tests()
