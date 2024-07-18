#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.dosimetry as rd
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test009")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # test
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    ct_input = data_folder / "ct_8mm.nii.gz"
    oar_json = data_folder / "oar_teff.json"
    output = output_folder / "dose.json"

    print('dose rate output computed with : ')
    cmd = f"rpt_dose_rate -s {spect_input} -r spect --ct {ct_input} -o {output_folder} -a 1e5"
    print(cmd)
    # cmd_ok = he.run_cmd(cmd, data_folder / "..")
    # (copy in data folder)

    s = 6974.43264  # this value is computed by rpt_dose_rate
    start_test("Hansscheid 2018 with dose rate: cmd")
    cmd = (f"rpt_dose -d {data_folder / 'test009' / 'output-dose.mhd'} -u Gy/s --ct {ct_input} -l {oar_json}"
           f" -o {output} -t 24 -m hanscheid2018_dose_rate --scaling {s}")
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(cmd_ok, f'cmd')

    # compare the ref dose
    start_test("Hanscheid 2018 with dose rate: compare dose rate")
    dose_ref = ref_folder / "dose_ref_hanscheid2018_dose_rate.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.05)
    stop_test(b, 'compare json dose')

    # compare to the conventional hanscheid (without dose_rate)
    start_test("Hanscheid 2018 with dose rate: compare dose (not rate)")
    # rpt_dose -s data/spect_8.321mm.nii.gz -u Bq --ct data/ct_8mm.nii.gz -l data/oar_teff.json
    # -o data/test009/dose_ref_hanscheid2018.json -t 24 -m hanscheid2018
    dose_ref = ref_folder / "dose_ref_hanscheid2018.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.2)
    stop_test(b, 'compare json dose')

    # test
    start_test("Hanscheid 2017 with dose rate")
    cmd = (f"rpt_dose -d {data_folder / 'test009' / 'output-dose.mhd'} -u Gy/s --ct {ct_input} -l {oar_json}"
           f" -o {output} -t 24 -m hanscheid2017_dose_rate --scaling {s}")
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(cmd_ok, 'cmd')

    # compare the ref dose
    dose_ref = ref_folder / "dose_ref_hanscheid2017_dose_rate.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.05)
    stop_test(b, 'compare the doses')

    # compare to the conventional hanscheid (without dose_rate)
    # rpt_dose -s data/spect_8.321mm.nii.gz -u Bq --ct data/ct_8mm.nii.gz -l data/oar_teff.json -o data/test009/dose_ref_hanscheid2017.json -t 24 -m hanscheid2017
    dose_ref = ref_folder / "dose_ref_hanscheid2017.json"
    b = rd.test_compare_json_doses(dose_ref, output, tol=0.2)
    stop_test(b, 'compare the doses')

    # end
    end_tests()
