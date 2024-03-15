#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as im
import rpt_dosi.helpers as he

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test resample (with gauss)
    # rpt_resample_roi -i data/roi.nii.gz -o data/test001/roi_9mm.nii.gz -s 9
    roi_input = data_folder / "rois" / "liver.nii.gz"
    roi_output = output_folder / "roi_test.nii.gz"
    cmd = f"rpt_resample_roi -i {roi_input} -o {roi_output} -s 7.5"
    is_ok = he.run_cmd(cmd, data_folder / "..")

    # compare
    roi_ref = ref_folder / "liver_7.5mm_ref.nii.gz"
    b = im.compare_images(roi_output, roi_ref)
    he.print_tests(b, f"Resample ROI {roi_output} vs {roi_ref}")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
