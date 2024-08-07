#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as he
from rpt_dosi.utils import start_test, stop_test, end_tests
import numpy as np

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test002b")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test resample (unit is assumed to be Bq)
    start_test('resample cmd line')
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_test.nii.gz"
    cmd = f"rpt_resample_spect -i {spect_input} -o {spect_output} -s 12 --sigma auto -u Bq"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, 'resample cmd line')

    # check total counts
    start_test('check total counts')
    spect1 = rim.read_spect(spect_input, 'Bq')
    tc_input = spect1.compute_total_activity()
    spect2 = rim.read_spect(spect_output)
    tc_output = spect2.compute_total_activity()
    diff = np.fabs(tc_input - tc_output) / tc_input * 100
    b = diff < 0.5
    stop_test(b, f'Total counts (Bq) = {tc_input}, {tc_output}  => {diff} %')

    # convert to BqmL
    start_test('convert to BqmL')
    sp = rim.read_spect(spect_input, 'Bq')
    sp.convert_to_bqml()
    like = rim.read_metaimage(spect_output)
    sp = rim.resample_spect_like(sp, like, "auto")
    sp.write(spect_output)
    spect2 = rim.read_spect(spect_output)
    tc_output = spect2.compute_total_activity()
    diff = np.fabs(tc_input - tc_output) / tc_input * 100
    b = diff < 0.5
    stop_test(b, f'Total counts (Bq/mL + like) = {tc_input}, {tc_output}  => {diff} %')

    # end
    end_tests()
