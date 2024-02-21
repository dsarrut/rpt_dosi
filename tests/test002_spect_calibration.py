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
    # rpt_spect_calibration -i data/spect_8.321mm.nii.gz -o data/test002/spect_activity_ref.nii.gz -c 0.666
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_activity.nii.gz"
    cmd = f"rpt_spect_calibration -i {spect_input} -o {spect_output} -c 0.666"
    is_ok = he.run_cmd(cmd, data_folder / "..")

    # compare
    spect_ref = ref_folder / "spect_activity_ref.nii.gz"
    b = im.test_compare_image_exact(spect_output, spect_ref)
    he.print_tests(b, f"SPECT calibration activity {spect_output}  vs  {spect_ref}")
    is_ok = b and is_ok

    # test activity concentration
    print()
    # rpt_spect_calibration -i data/spect_8.321mm.nii.gz -o data/test002/spect_activity_conc_ref.nii.gz -c 0.222 --concentration
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_activity_conc.nii.gz"
    cmd = f"rpt_spect_calibration -i {spect_input} -o {spect_output} -c 0.222 --concentration"
    is_ok = he.run_cmd(cmd, data_folder / "..") and is_ok

    # compare
    spect_ref = ref_folder / "spect_activity_conc_ref.nii.gz"
    b = im.test_compare_image_exact(spect_output, spect_ref)
    he.print_tests(
        b, f"SPECT calibration activity concentration {spect_output}  vs  {spect_ref}"
    )
    is_ok = b and is_ok

    # SUV
    print()
    # rpt_spect_Bq_to_SUV -i spect_8.321mm.nii.gz -o test002/spect_suv_ref.nii.gz --ia 7400 --bw 80
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_suv.nii.gz"
    cmd = f"rpt_spect_Bq_to_SUV -i {spect_input} -o {spect_output} --ia 7400 --bw 80"
    is_ok = he.run_cmd(cmd, data_folder / "..") and is_ok

    # compare
    spect_ref = ref_folder / "spect_suv_ref.nii.gz"
    b = im.test_compare_image_exact(spect_output, spect_ref)
    he.print_tests(
        b, f"SPECT SUV {spect_output}  vs  {spect_ref}"
    )
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
