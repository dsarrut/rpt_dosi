#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import rpt_dosi.helpers as he
import os

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test004")
    is_ok = True
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test
    # rpt_dose_hanscheid -s data/spect_8.321mm.nii.gz  --ct data/ct_8mm.nii.gz  -l data/oar.json -o a.txt -t 24 -m 2017
    print("Hanscheid 2017 method")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_realpath.json"
    output = output_folder / "dose.json"
    cmd = f"cd {data_folder}/.. ; rpt_dose_hanscheid -s {spect_input} --ct {ct_input} -l {oar_json} -o {output} -t 24 -m 2017"
    print(cmd)
    os.system(cmd)
    dose_ref = ref_folder / "dose_ref_2017.json"

    # open the dose files
    with open(output) as f:
        dose = json.load(f)
    with open(dose_ref) as f:
        dose_ref = json.load(f)
    print(dose)
    # remove date key
    del dose["date"]
    del dose_ref["date"]
    # compare
    b = dose == dose_ref
    he.print_tests(b, f"Compare doses")
    is_ok = b and is_ok

    # test
    # rpt_dose_hanscheid -s data/spect_8.321mm.nii.gz  --ct data/ct_8mm.nii.gz  -l data/oar.json -o a.txt -t 24 -m 2018
    print()
    print("Hanscheid 2018 method")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_realpath.json"
    output = output_folder / "dose.json"
    cmd = f"cd {data_folder}/.. ; rpt_dose_hanscheid -s {spect_input} --ct {ct_input} -l {oar_json} -o {output} -t 24 -m 2018"
    print(cmd)
    os.system(cmd)
    dose_ref = ref_folder / "dose_ref_2018.json"

    # open the dose files
    with open(output) as f:
        dose = json.load(f)
    with open(dose_ref) as f:
        dose_ref = json.load(f)
    print(dose)
    # remove date key
    del dose["date"]
    del dose_ref["date"]
    # compare
    b = dose == dose_ref
    he.print_tests(b, f"Compare doses")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
