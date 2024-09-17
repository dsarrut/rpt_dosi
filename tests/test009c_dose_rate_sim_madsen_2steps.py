#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.dosimetry as rd

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test009c")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    try:
        import opengate
    except:
        print(f'GATE is not available, test {__file__} is skipped')
        exit(0)

    # data
    spect_input = data_folder / "p12_10.0mm" / "cycle1" / "tp2" / "spect.nii.gz"
    ct_input = data_folder / "p12_10.0mm" / "cycle1" / "tp2" / "ct.nii.gz"
    output = output_folder / "dose.json"
    oar_json = data_folder / "test009" / "oar_teff.json"

    # test
    print("Dose rate: GATE simulation")
    cmd = f"rpt_dose_rate -s {spect_input} -r spect --ct {ct_input} -o {output_folder} -a 2e5"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")

    print("Madsen with dose rate")
    cmd = (f"rpt_dose -d {output_folder / 'output_dose.nii.gz'} -u Gy/s --ct {ct_input} -l {oar_json}"
           f" -o {output} -m madsen2018_dose_rate")
    cmd_ok = he.run_cmd(cmd, data_folder / "..") and cmd_ok

    # compare the ref dose
    dose_ref = ref_folder / "dose_ref_madsen2018_dose_rate.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output, tol=0.05) and cmd_ok

    # compare to the conventional madsen (without dose_rate)
    dose_ref = ref_folder / "dose_ref_madsen2018.json"
    is_ok = rd.test_compare_json_doses(dose_ref, output, tol=0.2) and cmd_ok and is_ok

    # end
    he.test_ok(is_ok)
