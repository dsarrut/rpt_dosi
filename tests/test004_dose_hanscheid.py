#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.helpers as he
import rpt_dosi.dosimetry as rd

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test004")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test
    print("Hanscheid 2017 method with default Teff")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar.json"
    output = output_folder / "dose.json"
    cmd = f"rpt_dose -s {spect_input} --ct {ct_input} -l {oar_json} -o {output} -t 24 -m hanscheid2017"
    is_ok = he.run_cmd(cmd, data_folder / "..")

    # open the dose files
    dose_ref = ref_folder / "dose_ref_2017.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output) and is_ok

    # test
    print()
    print("Hanscheid 2017 method with Teff in oar.json file")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_teff.json"
    output = output_folder / "dose.json"
    cmd = f"rpt_dose -s {spect_input} --ct {ct_input} -l {oar_json} -o {output} -t 24 -m hanscheid2017"
    is_ok = he.run_cmd(cmd, data_folder / "..") and is_ok

    # compare the dose files
    dose_ref = ref_folder / "dose_ref_2017.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output) and is_ok

    # test
    print()
    print("Hanscheid 2018 method")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar.json"
    output = output_folder / "dose.json"
    cmd = f"rpt_dose -s {spect_input} --ct {ct_input} -l {oar_json} -o {output} -t 24 -m hanscheid2018"
    is_ok = he.run_cmd(cmd, data_folder / "..") and is_ok

    # compare the dose files
    dose_ref = ref_folder / "dose_ref_2018.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output) and is_ok

    # end
    he.test_ok(is_ok)
