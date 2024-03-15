#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.helpers as he
import rpt_dosi.dosimetry as rd

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test009")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test
    print()
    print("Dose rate")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_teff.json"
    output = output_folder / "dose.json"

    cmd = f"rpt_dose_rate -s {spect_input} -r spect --ct {ct_input} -o {output_folder} -a 1e4"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")

    s = 69744.3264
    print("Madsen with dose rate")
    cmd = (f"rpt_dose -s {output_folder / 'output-dose.mhd'} -u Gy_sec --ct {ct_input} -l {oar_json}"
           f" -o {output} -t 24 -m madsen2018_dose_rate --scaling {s}")
    cmd_ok = he.run_cmd(cmd, data_folder / "..") and cmd_ok

    # compare the dose files
    dose_ref = ref_folder / "dose_ref_madsen2018.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output, tol=0.1) and cmd_ok

    # end
    he.test_ok(is_ok)
