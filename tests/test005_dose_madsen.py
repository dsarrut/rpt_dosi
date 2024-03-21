#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.helpers as he
import rpt_dosi.dosimetry as rd
import rpt_dosi.images as rim
import json

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test009")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test
    print("Madsen 2018 method with Teff")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_teff.json"
    output = output_folder / "dose.json"

    # read images
    ct = rim.read_ct(ct_input)
    spect = rim.read_spect(spect_input)
    spect.unit = 'Bq'
    spect.time_from_injection_h = 24.0
    # warning how to keep coherence with injection time + acquisition time?

    # read rois
    rois = rim.read_list_of_rois(oar_json)

    # compute dose
    d = rd.DoseMadsen2018(ct, spect)
    d.resample_like = "spect"
    d.gaussian_sigma = 'auto'
    doses = d.run(rois)

    # save output to json and print
    with open(output, "w") as f:
        json.dump(doses, f, indent=4)
    for d in doses:
        print(f'{d} = {doses[d]}')

    # compare the dose files
    dose_ref = ref_folder / "dose_ref_madsen2018.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output)

    # end
    he.test_ok(is_ok)
