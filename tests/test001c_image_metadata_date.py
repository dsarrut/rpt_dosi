#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as he
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001c")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # input image
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    output = output_folder / "spect_8.321mm.nii.gz"

    # read as spect
    s = rim.read_spect(spect_input, 'Bq')

    # write elsewhere with json
    s.write(output)
    s2 = rim.read_spect(output)

    # set value
    start_test('set the time from injection')
    print(f'{s2.acquisition_datetime=}')
    print(f'{s2.injection_datetime=}')
    s2.time_from_injection_h = 24
    print(f'{s2.acquisition_datetime=}')
    print(f'{s2.injection_datetime=}')
    b = s2.time_from_injection_h == 24
    stop_test(b, f'Set the time from injection to 24 = {s2.time_from_injection_h}')

    # set value
    start_test('set the time from injection')
    try:
        s2.time_from_injection_h = 36
        b = False
    except:
        b = True
    stop_test(b, 'OK cannot set the time from injection')

    # change the time
    start_test('set the acquisition time')
    s2.acquisition_datetime = "1970-01-02 12:00:00"
    b = s2.time_from_injection_h == 36
    stop_test(b, f'must be 36 = {s2.time_from_injection_h}')

    # set time from injection
    start_test('set the time from injection when acquisition time is None')
    s2.acquisition_datetime = None
    try:
        print(s2.time_from_injection_h)
        b = False
    except:
        b = True
    stop_test(b, 'Can set the time from injection ?')
    s2.injection_datetime = None

    # set time from injection
    start_test('set back the time from injection')
    s2.time_from_injection_h = 24
    b = s2.time_from_injection_h == 24
    stop_test(b, f'must be 24 = {s2.time_from_injection_h}')

    # set time from injection
    start_test('set injection datetime and acquisition time')
    s2.injection_datetime = "2020 12 03 11:00"
    s2.acquisition_datetime = "2020 12 04 11:00"
    b = s2.time_from_injection_h == 24
    stop_test(b, f'must be 24 = {s2.time_from_injection_h}')

    # end
    end_tests()
