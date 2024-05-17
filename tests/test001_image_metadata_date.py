#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.helpers as he
import shutil
import os

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # input image
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    output = output_folder / "spect_8.321mm.nii.gz"

    # read as spect
    s = rim.read_spect(spect_input, 'Bq')
    print(s)

    # write with json
    s.write(output)
    s2 = rim.read_spect(output)
    print(s2)

    # set value
    print('set the time from injection')
    s2.time_from_injection_h = 24
    print(s2)
    is_ok = s2.time_from_injection_h == 24
    try:
        s2.time_from_injection_h = 36
        is_ok = False
    except:
        he.print_tests(is_ok, 'OK cannot set the time from injection')

    # change the time
    print()
    print('set the acquisition time')
    s2.acquisition_datetime = "1970-01-02 12:00:00"
    is_ok = s2.time_from_injection_h == 36 and is_ok
    he.print_tests(is_ok, f'must be 36 = {s2.time_from_injection_h}')

    #
    s2.acquisition_datetime = None
    try:
        print(s2.time_from_injection_h)
        is_ok = False
    except:
        he.print_tests(is_ok, 'OK cannot set the time from injection')
    s2.injection_datetime = None
    s2.time_from_injection_h = 24
    is_ok = s2.time_from_injection_h == 24 and is_ok
    he.print_tests(is_ok, f'must be 24 = {s2.time_from_injection_h}')

    # end
    he.test_ok(is_ok)
