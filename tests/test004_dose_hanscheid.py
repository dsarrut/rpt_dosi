#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.dosimetry as rd
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test004")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # test
    start_test("Hanscheid 2017 method with Teff in oar.json file (cmd line)")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_teff.json"
    output = output_folder / "dose.json"
    cmd = f"rpt_dose -s {spect_input} -u Bq -r spect --ct {ct_input} -l {oar_json} -o {output} -t 24 -m hanscheid2017"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, 'cmd rpt_dose')

    # compare the dose files
    start_test('compare')
    dose_ref = ref_folder / "dose_ref_2017.json"
    b = rd.test_compare_json_doses(dose_ref, output)
    stop_test(b, 'compare with dose ref')

    # test
    start_test("Hanscheid 2018 method (cmd line)")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar.json"
    output = output_folder / "dose.json"
    cmd = f"rpt_dose -s {spect_input} -u Bq --ct {ct_input} -l {oar_json} -o {output} -t 24 -m hanscheid2018"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, 'cmd')

    # compare the dose files
    start_test('compare')
    dose_ref = ref_folder / "dose_ref_2018.json"
    b = rd.test_compare_json_doses(dose_ref, output)
    stop_test(b, 'compare with dose ref')

    # end
    end_tests()
