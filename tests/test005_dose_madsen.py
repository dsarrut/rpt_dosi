#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.dosimetry as rd
import rpt_dosi.images as rim
import json
import os
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test005")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # test
    start_test("Madsen 2018 method with Teff (function)")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_teff.json"
    output = output_folder / "dose.json"

    # read images
    ct = rim.read_ct(ct_input)
    spect = rim.read_spect(spect_input, 'Bq')
    spect.time_from_injection_h = 24.0
    # warning how to keep coherence with injection time + acquisition time?

    # read rois
    rois = rim.read_list_of_rois(oar_json, os.path.join(data_folder, "../"))

    # compute dose
    d = rd.DoseMadsen2018(ct, spect)
    d.resample_like = "spect"
    d.gaussian_sigma = 'auto'
    d.phantom = "ICRP 110 AM"
    doses = d.run(rois)

    # save output to json and print
    with open(output, "w") as f:
        json.dump(doses, f, indent=4)
    for do in doses:
        print(f'{do} = {doses[do]}')

    # compare the dose files
    dose_ref = ref_folder / "dose_ref_madsen2018.json"
    print(dose_ref)
    print(output)
    b = rd.test_compare_json_doses(dose_ref, output)
    stop_test(b, "Madsen 2018 method with Teff (function)")

    # compute dose
    start_test("Madsen 2018 method with resample like ct")
    output = output_folder / "dose_ct.json"
    d.resample_like = "ct"
    doses = d.run(rois)

    # save output to json and print
    with open(output, "w") as f:
        json.dump(doses, f, indent=4)
    for do in doses:
        print(f'{do} = {doses[do]}')

    # compare the dose files
    dose_ref = ref_folder / "dose_ref_madsen2018_ct.json"
    b = rd.test_compare_json_doses(dose_ref, output)
    stop_test(b, "Madsen 2018 method resample like ct ")

    # compare the dose files
    start_test('compare resample spect vs resample ct, tolerance 14%')
    dose_ref = ref_folder / "dose_ref_madsen2018.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.14)
    stop_test(b, 'compare with ref')

    # end
    end_tests()
