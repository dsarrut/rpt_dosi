#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.helpers as he

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test002")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test activity
    print()
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_activity.nii.gz"
    spect = rim.read_spect(spect_input)
    s = spect.voxel_volume_ml / 0.666
    cmd = f"rpt_image_update -i {spect_input} -u Bq -o {spect_output} -s {s} -t SPECT"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")

    # compare
    spect_ref = ref_folder / "spect_activity_ref.nii.gz"
    b = rim.test_compare_images(spect_output, spect_ref, tol=1e-6)
    he.print_tests(b, f"SPECT calibration activity {spect_output}  vs  {spect_ref}")
    is_ok = b and cmd_ok

    # test activity concentration
    print()
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_activity_conc.nii.gz"
    # read as Bq
    cmd = f"rpt_image_update -i {spect_input} -u Bq -o {spect_output} -t SPECT"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    # convert as BqmL, scale
    cmd = f"rpt_image_update -i {spect_output} -u Bq/mL -o {spect_output} -s {s}"
    cmd_ok = he.run_cmd(cmd, data_folder / "..") and cmd_ok
    # convert back as Bq
    cmd = f"rpt_image_update -i {spect_output} -u Bq -o {spect_output}"
    cmd_ok = he.run_cmd(cmd, data_folder / "..") and cmd_ok

    # compare
    b = rim.test_compare_images(spect_output, spect_ref, tol=1e-6)
    he.print_tests(
        b and cmd_ok, f"SPECT calibration activity concentration {spect_output}  vs  {spect_ref}"
    )
    is_ok = b and cmd_ok and is_ok

    # SUV
    print()
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_suv.nii.gz"
    # read as Bq
    cmd = f"rpt_image_update -i {spect_input} -u Bq -o {spect_output} -t SPECT"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    # convert as SUV
    cmd = f"rpt_image_update -i {spect_output} -u SUV -o {spect_output} --ia 7400 --bw 80"
    cmd_ok = he.run_cmd(cmd, data_folder / "..") and cmd_ok

    # compare
    spect_ref = ref_folder / "spect_suv_ref.nii.gz"
    b = rim.test_compare_images(spect_output, spect_ref)
    he.print_tests(
        b and cmd_ok, f"SPECT SUV {spect_output}  vs  {spect_ref}"
    )
    is_ok = b and cmd_ok and is_ok

    # end
    he.test_ok(is_ok)
