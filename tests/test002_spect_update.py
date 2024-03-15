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

    # test activity
    print()
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_activity.nii.gz"
    spect = im.read_spect(spect_input, "Bq")
    s = spect.voxel_volume_ml / 0.666
    cmd = f"rpt_spect_update -i {spect_input} -u Bq -o {spect_output} -c {s}"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")

    # compare
    spect_ref = ref_folder / "spect_activity_ref.nii.gz"
    b = im.compare_images(spect_output, spect_ref, tol=1e-6)
    he.print_tests(b, f"SPECT calibration activity {spect_output}  vs  {spect_ref}")
    is_ok = b and cmd_ok

    # test activity concentration
    print()
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_activity_conc.nii.gz"
    spect = im.read_spect(spect_input, "Bq")
    s = 1 / 0.222
    cmd = f"rpt_spect_update -i {spect_input} -u BqmL -o {spect_output} -c {s}"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")

    # compare
    spect_ref = ref_folder / "spect_activity_conc_ref.nii.gz"
    b = im.compare_images(spect_output, spect_ref, tol=1e-6)
    he.print_tests(
        b and cmd_ok, f"SPECT calibration activity concentration {spect_output}  vs  {spect_ref}"
    )
    is_ok = b and cmd_ok and is_ok

    # SUV
    print()
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_suv.nii.gz"
    cmd = f"rpt_spect_update -i {spect_input} -u Bq -o {spect_output} --ia 7400 --bw 80 --output_unit SUV"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")

    # compare
    spect_ref = ref_folder / "spect_suv_ref.nii.gz"
    b = im.compare_images(spect_output, spect_ref)
    he.print_tests(
        b and cmd_ok, f"SPECT SUV {spect_output}  vs  {spect_ref}"
    )
    is_ok = b and cmd_ok and is_ok

    # end
    he.test_ok(is_ok)
