#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.dosimetry as rd
import rpt_dosi.images as rim
import os
import numpy as np

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test010")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_teff.json"
    output = output_folder / "dose.json"

    # read images
    ct = rim.read_ct(ct_input)
    spect = rim.read_spect(spect_input, 'Bq')
    spect.time_from_injection_h = 72.0
    rois = rim.read_list_of_rois(oar_json, os.path.join(data_folder, "../"))

    # compute dose
    d = rd.DoseMadsen2018(ct, spect)
    d.resample_like = "spect"
    d.gaussian_sigma = 'auto'
    d.phantom = "ICRP 110 AM"
    doses_madsen2018 = d.run(rois)

    d = rd.DoseHanscheid2017(ct, spect)
    d.resample_like = "spect"
    d.gaussian_sigma = 'auto'
    d.phantom = "ICRP 110 AM"
    doses_hanscheid2017 = d.run(rois)

    d = rd.DoseHanscheid2018(ct, spect)
    d.resample_like = "spect"
    d.gaussian_sigma = 'auto'
    d.phantom = "ICRP 110 AM"
    doses_hanscheid2018 = d.run(rois)

    # compare
    tol = 6
    is_ok = True
    print(f'madsen2018   hanscheid2017   hanscheid2018')
    for roi in rois:
        a = doses_madsen2018[roi.name].dose_Gy
        b = doses_hanscheid2017[roi.name].dose_Gy
        c = doses_hanscheid2018[roi.name].dose_Gy
        max_diff = max(np.fabs(a - b), np.fabs(a - c), np.fabs(b - c)) / max(a, b, c) * 100
        print(f'{roi.name:<20} : {a:.2f}  {b:.2f}  {c:.2f}   -> {max_diff:.2f} %')
        is_ok = max_diff < tol and is_ok

    # end
    he.test_ok(is_ok)
