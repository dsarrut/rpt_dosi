#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.helpers as he
from rpt_dosi.helpers import warning

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
    print()
    warning('set the time from injection')
    print(f'{s2.acquisition_datetime=}')
    print(f'{s2.injection_datetime=}')
    s2.time_from_injection_h = 24
    print(f'{s2.acquisition_datetime=}')
    print(f'{s2.injection_datetime=}')
    ok = s2.time_from_injection_h == 24
    he.print_tests(ok, f'Set the time from injection to 24 = {s2.time_from_injection_h}')

    # set value
    print()
    warning('set the time from injection')
    try:
        s2.time_from_injection_h = 36
        ok = False
    except:
        pass
    ok = he.print_tests(ok, 'OK cannot set the time from injection') and ok

    # change the time
    print()
    warning('set the acquisition time')
    s2.acquisition_datetime = "1970-01-02 12:00:00"
    b = s2.time_from_injection_h == 36
    ok = he.print_tests(b, f'must be 36 = {s2.time_from_injection_h}') and ok

    # set time from injection
    print()
    warning('set the time from injection when acquisition time is None')
    s2.acquisition_datetime = None
    try:
        print(s2.time_from_injection_h)
        ok = False
    except:
        pass
    ok = he.print_tests(ok, 'Can set the time from injection ?') and ok
    s2.injection_datetime = None

    # set time from injection
    print()
    warning('set back the time from injection')
    s2.time_from_injection_h = 24
    b = s2.time_from_injection_h == 24
    ok = he.print_tests(b, f'must be 24 = {s2.time_from_injection_h}') and ok

    # set time from injection
    print()
    warning('set injection datetime and acquisition time')
    s2.injection_datetime = "2020 12 03 11:00"
    s2.acquisition_datetime = "2020 12 04 11:00"
    b = s2.time_from_injection_h == 24
    ok = he.print_tests(b, f'must be 24 = {s2.time_from_injection_h}') and ok

    # end
    he.test_ok(ok)
