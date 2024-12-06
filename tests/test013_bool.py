#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rpt_dosi.images as rim
import rpt_dosi.utils as he
from rpt_dosi.utils import start_test, stop_test, end_tests
import SimpleITK as sitk

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test013")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # consider several mask image and merge them with AND
    start_test('Boolean operator "and" between 3 ROIs')
    # data/p12_10.0mm/cycle1/tp2
    db_folder = data_folder / "p12_10.0mm" / "cycle1" / "tp2" / "rois_crop"
    mask_filenames = [
        "liver_crop.nii.gz",
        "right_kidney_crop.nii.gz",
        "spleen_crop.nii.gz",
    ]

    mimg1 = rim.read_roi(db_folder / mask_filenames[0])
    img1 = mimg1.image
    for mask_filename in mask_filenames[1:]:
        mimg2 = rim.read_roi(db_folder / mask_filename)
        img1 = rim.roi_boolean_operation(img1, mimg2.image, "or")

    # final crop
    img1 = rim.crop_to_bounding_box(img1, lover_threshold=0)
    sitk.WriteImage(img1, output_folder / "bool.mhd")

    # compare with ref
    ref = ref_folder / "bool.mhd"
    b = rim.test_compare_images(output_folder / "bool.mhd", ref)
    stop_test(b, f"Check bool 'and'")
    is_ok = b

    # check command line
    start_test("Same with the command line")
    cmd = "rpt_roi_bool "
    for m in mask_filenames:
        cmd += f"{str(db_folder / m)} "
    cmd += f'-o {output_folder / "bool2.mhd"}'
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, f"command line")

    # compare with ref
    ref = output_folder / "bool.mhd"
    b = rim.test_compare_images(output_folder / "bool2.mhd", ref)
    stop_test(b, f"Check bool 'and'")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
