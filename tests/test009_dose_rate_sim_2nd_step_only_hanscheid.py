#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.dosimetry as rd
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test009a")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # test
    spect_input = data_folder / "p12_10.0mm" / "cycle1" / "tp2" / "spect.nii.gz"
    ct_input = data_folder / "p12_10.0mm" / "cycle1" / "tp2" / "ct.nii.gz"
    output = output_folder / "dose.json"
    gate_dose_ref = data_folder / 'test009' / 'output-dose.mhd'
    oar_json = data_folder / "test009" / "oar_teff.json"

    """    
    
    References:
    
    # Direct dose computation with hanscheid2018
    rpt_dose -s data/p12_10.0mm/cycle1/tp2/spect.nii.gz --ct data/p12_10.0mm/cycle1/tp2/ct.nii.gz -l data/test009/oar_teff.json -m hanscheid2018 -o data/test009a/dose_ref_hanscheid2018.json
    
    # Dose rate
    rpt_dose_rate -s data/p12_10.0mm/cycle1/tp2/spect.nii.gz -r spect --ct data/p12_10.0mm/cycle1/tp2/ct.nii.gz -o data/test009 -a 1e5
    
    # Dose computation with dose rate and hanscheid2018
    rpt_dose -d data/test009/output-dose.mhd --ct data/p12_10.0mm/cycle1/tp2/ct.nii.gz -l data/test009/oar_teff.json -m hanscheid2018_dose_rate -u Gy/s -t 24.73 --scaling 12502.213127629648  -o data/test009a/dose_ref_hanscheid2018_dose_rate.json
    
    # Direct dose computation with hanscheid2017
    rpt_dose -s data/p12_10.0mm/cycle1/tp2/spect.nii.gz --ct data/p12_10.0mm/cycle1/tp2/ct.nii.gz -l data/test009/oar_teff.json -m hanscheid2017 -o data/test009a/dose_ref_hanscheid2017.json
        
    # Dose computation with dose rate and hanscheid2017
    rpt_dose -d data/test009/output-dose.mhd --ct data/p12_10.0mm/cycle1/tp2/ct.nii.gz -l data/test009/oar_teff.json -m hanscheid2017_dose_rate -u Gy/s -t 24.73 --scaling 12502.213127629648 -o data/test009a/dose_ref_hanscheid2017_dose_rate.json
    
    """

    print('dose rate output computed with : ')
    cmd = f"rpt_dose_rate -s {spect_input} -r spect --ct {ct_input} -o {output_folder} -a 1e5"
    print(cmd)
    # FIXME this is not run here because require gate to be installed in the github actions
    # cmd_ok = he.run_cmd(cmd, data_folder / "..")
    # (copied in data folder)
    s = 12502.213127629648  # this value is computed by rpt_dose_rate

    start_test("Hanscheid 2018 with dose rate: cmd")
    cmd = (f"rpt_dose -d {gate_dose_ref} -u Gy/s --ct {ct_input} -l {oar_json}"
           f" -o {output} -t 24.73 -m hanscheid2018_dose_rate --scaling {s}")
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(cmd_ok, f'cmd')

    # compare the ref dose
    start_test("Hanscheid 2018 with dose rate: compare dose rate")
    dose_ref = ref_folder / "dose_ref_hanscheid2018_dose_rate.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.1)
    stop_test(b, 'compare json dose')

    # compare to the conventional hanscheid (without dose_rate)
    start_test("Hanscheid 2018 with dose rate: compare dose (no dose rate)")
    dose_ref = ref_folder / "dose_ref_hanscheid2018.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.6)
    stop_test(b, 'compare json dose')

    # test
    start_test("Hanscheid 2017 with dose rate, cmd line")
    cmd = (f"rpt_dose -d {gate_dose_ref} -u Gy/s --ct {ct_input} -l {oar_json}"
           f" -o {output} -t 24.73 -m hanscheid2017_dose_rate --scaling {s}")
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(cmd_ok, 'cmd')

    # compare the ref dose
    start_test("Hanscheid 2017 with dose rate")
    dose_ref = ref_folder / "dose_ref_hanscheid2017_dose_rate.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.07)
    stop_test(b, 'compare the doses')

    # compare to the conventional hanscheid (without dose_rate)
    start_test("Hanscheid 2017 without dose rate")
    dose_ref = ref_folder / "dose_ref_hanscheid2017.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.35)
    stop_test(b, 'compare the doses')

    # end
    end_tests()
