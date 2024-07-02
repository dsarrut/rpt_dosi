#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.dosimetry as rd

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test009")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test
    print("Dose rate: GATE simulation")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_teff.json"
    output = output_folder / "dose.json"

    # cmd = f"rpt_dose_rate -s {spect_input} -r spect --ct {ct_input} -o {output_folder} -a 1e5"
    # cmd_ok = he.run_cmd(cmd, data_folder / "..")

    s = 6974.43264  # this value is computed by rpt_dose_rate
    print("Madsen with dose rate")
    cmd = (f"rpt_dose -d {data_folder / 'test009' / 'output-dose.mhd'} -u Gy/s --ct {ct_input} -l {oar_json}"
           f" -o {output} -t 24 -m madsen2018_dose_rate --scaling {s}")
    cmd_ok = he.run_cmd(cmd, data_folder / "..")

    # compare the ref dose
    dose_ref = ref_folder / "dose_ref_madsen2018_dose_rate.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output, tol=0.05) and cmd_ok

    # compare to the conventional madsen (without dose_rate)
    dose_ref = ref_folder / "dose_ref_madsen2018.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output, tol=0.2) and cmd_ok and is_ok

    # end
    he.test_ok(is_ok)
