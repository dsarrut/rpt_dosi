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

    # set meta unit Bq
    print()
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_8.321mm.nii.gz"
    shutil.copy(spect_input, spect_output)
    a = str(spect_output) + '.json'
    if os.path.exists(a):
        os.remove(a)
    cmd = f"rpt_image_set_metadata -i {spect_output} -u Bq -t SPECT"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    out_spect = rim.read_spect(spect_output)
    is_ok = out_spect.image_type == 'SPECT' and out_spect.unit == 'Bq' and cmd_ok
    he.print_tests(is_ok, f'(read spect) Set metadata read SPECT and Bq ? {is_ok}')

    # set meta again with already existing metadata
    print()
    spect = rim.read_image(spect_output)
    try:
        spect.unit = 'Bq/mL'
    except he.Rpt_Error:
        he.print_tests(is_ok, f'OK cannot set unit because already there {is_ok}')
    is_ok = spect.image_type == 'SPECT' and spect.unit == 'Bq' and is_ok
    he.print_tests(is_ok, f'(read image) Set metadata read SPECT and Bq ? {is_ok}')

    # set meta unit Bq/mL
    print()
    cmd = f"rpt_image_set_metadata -i {spect_output} -u Bq/mL -t SPECT -f"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    out_spect = rim.read_spect(spect_output)
    is_ok = out_spect.image_type == 'SPECT' and out_spect.unit == 'Bq/mL' and cmd_ok
    he.print_tests(is_ok, f'(read spect) Set metadata read SPECT and Bq/mL ? {is_ok}')

    # set tags for spect
    print()
    cmd = (f'rpt_image_set_metadata -i {spect_output}'
           f' --tag injection_datetime "2022-02-01 12:11:00"'
           f' --tag injection_activity_mbq 7504'
           f' --tag acquisition_datetime "2022-02-01 18:11:00"'
           f' --tag body_weight_kg 70.4 -v')
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    he.print_tests(cmd_ok, f'cmd ? {cmd_ok}')

    # special case for time_from_injection_h
    print()
    spect = rim.read_image(spect_output)
    spect.body_weight_kg = 80.4
    spect.acquisition_datetime = None
    spect.injection_datetime = None
    spect.time_from_injection_h = 12.4
    print(spect.acquisition_datetime)
    is_ok = spect.acquisition_datetime == "1970-01-01 12:24:00" and cmd_ok and is_ok
    he.print_tests(is_ok, f'correct date ? {is_ok}')

    # special case for time_from_injection_h
    print()
    spect = rim.read_image(spect_output)
    try:
        spect.time_from_injection_h = 12.4
        is_ok = False
    except he.Rpt_Error:
        he.print_tests(is_ok, f'OK cannot set time from injection tag {is_ok}')

    # set wrong tag
    print()
    spect = rim.read_image(spect_output)
    try:
        spect.set_metadata("toto", 'titi')
        is_ok = False
        he.print_tests(is_ok, f'ERROR can set wrong tag  {is_ok}')
    except he.Rpt_Error:
        he.print_tests(is_ok, f'OK cannot set wrong tag {is_ok}')

    # set wrong tag
    print()
    ct_input = data_folder / "ct_8mm.nii.gz"
    ct = rim.read_ct(ct_input)
    try:
        ct.set_metadata("injection_datetime", 'titi')
        is_ok = False
        he.print_tests(is_ok, f'ERROR can set tag date to wrong value {is_ok}')
    except he.Rpt_Error:
        he.print_tests(is_ok, f'OK cannot set tag date to wrong value {is_ok}')

    # set wrong tag type
    # NO TYPE CHECK YET
    """print()
    spect = rim.read_image(spect_output)
    try:
        spect.set_metadata("injection_activity_mbq", 'tutu')
        is_ok = False
        he.print_tests(is_ok, f'ERROR can set tag float to wrong value {is_ok}')
        print(spect.info())
    except he.Rpt_Error:
        he.print_tests(is_ok, f'OK cannot set tag float to wrong value {is_ok}')
    """

    # end
    he.test_ok(is_ok)
