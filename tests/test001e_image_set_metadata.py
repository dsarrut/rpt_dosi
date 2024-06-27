#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.helpers as he
from rpt_dosi.helpers import warning
import math
import shutil
import os
import json

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001e")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()
    is_ok = True

    # prepare
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_activity.nii.gz"
    rim.delete_metadata(spect_output)
    spect = rim.read_spect(spect_input, 'Bq')
    spect.write(spect_output)

    # test
    warning(f'set metadata from cmd line')
    cmd = f"rpt_image_set_metadata -i {spect_output} --tag injection_activity_mbq 7400 --tag body_weight_kg 80"
    is_ok = he.run_cmd(cmd, data_folder / "..") and is_ok
    sp = rim.read_spect(spect_output)
    print(sp)
    b = sp.injection_activity_mbq == 7400
    is_ok = he.print_tests(b, f'Test injection activity mbq = {b}') and is_ok
    b = sp.body_weight_kg == 80
    is_ok = he.print_tests(b, f'Test body_weight_kg = {b}') and is_ok
    sp.write()
    t1 = sp.compute_total_activity()

    # test
    print()
    warning(f'set metadata from cmd line')
    cmd = f"rpt_image_set_metadata -i {spect_output} --unit SUV --tag description toto"
    is_ok = he.run_cmd(cmd, data_folder / "..") and is_ok
    sp = rim.read_spect(spect_output)
    t2 = sp.compute_total_activity()
    ok = math.isclose(t1, t2, rel_tol=1e-6)
    he.print_tests(ok, f'Compare total activity {t1} and {t2}')

    # test
    # set meta unit Bq
    print()
    warning('Test command line rpt_image_set_metadata with spect')
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
    warning('Test read_image')
    spect = rim.read_image(spect_output)
    try:
        spect.unit = 'Bq/mL'
        is_ok = False
    except he.Rpt_Error:
        pass
    he.print_tests(is_ok, f'OK cannot set unit because already there {is_ok}')
    is_ok = spect.image_type == 'SPECT' and spect.unit == 'Bq' and is_ok
    he.print_tests(is_ok, f'(read image) Set metadata read SPECT and Bq ? {is_ok}')

    # check filename in the json file
    print()
    warning('Test metadata json file')
    fn = spect.metadata_file_path
    with open(fn, 'r') as f:
        data = json.load(f)
        data['filename'] = "titi.nii.gz"
    with open(fn, 'w') as f:
        json.dump(data, f)
    try:
        spect = rim.read_image(spect_output)
        is_ok = False
    except he.Rpt_Error:
        pass
    he.print_tests(is_ok, f'OK cannot read with wrong filename tag {is_ok}')

    # check wrong but existing json file
    open(fn, 'w').close()
    try:
        spect = rim.read_image(spect_output)
        is_ok = False
    except he.Rpt_Error:
        pass
    he.print_tests(is_ok, f'OK cannot read wrong file {is_ok}')

    # (OLD TESTS)
    # set meta unit Bq/mL
    print()
    warning('Test set unit with rpt_image_set_metadata')
    cmd = f"rpt_image_set_metadata -i {spect_output} -u Bq/mL -t SPECT -f"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    out_spect = rim.read_spect(spect_output)
    is_ok = out_spect.image_type == 'SPECT' and out_spect.unit == 'Bq/mL' and cmd_ok
    is_ok = he.print_tests(is_ok, f'(read spect) Set metadata read SPECT and Bq/mL ? {is_ok}') and is_ok

    # set tags for spect
    print()
    warning('Test set tags rpt_image_set_metadata')
    cmd = (f'rpt_image_set_metadata -i {spect_output}'
           f' --tag injection_datetime "2022-02-01 12:11:00"'
           f' --tag injection_activity_mbq 7504'
           f' --tag acquisition_datetime "2022-02-01 18:11:00"'
           f' --tag body_weight_kg 70.4 -v')
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    is_ok = he.print_tests(cmd_ok, f'cmd ? {cmd_ok}') and is_ok

    # special case for time_from_injection_h
    print()
    warning('Test acquisition_datetime')
    spect = rim.read_image(spect_output)
    spect.body_weight_kg = 80.4
    spect.acquisition_datetime = None
    spect.injection_datetime = None
    spect.time_from_injection_h = 12.4
    print(spect.acquisition_datetime)
    is_ok = spect.acquisition_datetime == "1970-01-01 12:24:00" and cmd_ok and is_ok
    is_ok = he.print_tests(is_ok, f'correct date ? {is_ok}') and is_ok

    # special case for time_from_injection_h
    print()
    warning('Test time_from_injection_h')
    spect = rim.read_image(spect_output)
    try:
        spect.time_from_injection_h = 12.4
        is_ok = False
    except he.Rpt_Error:
        pass
    is_ok = he.print_tests(is_ok, f'OK cannot set time from injection tag {is_ok}') and is_ok

    # set wrong tag
    print()
    warning('Test wrong metadata')
    spect = rim.read_image(spect_output)
    try:
        spect.set_metadata("toto", 'titi')
        is_ok = False
    except he.Rpt_Error:
        pass
    is_ok = he.print_tests(is_ok, f'OK cannot set wrong tag {is_ok}') and is_ok

    # set wrong tag
    print()
    warning('Test wrong tag date type')
    ct_input = data_folder / "ct_8mm.nii.gz"
    ct = rim.read_ct(ct_input)
    try:
        ct.set_metadata("injection_datetime", 'titi')
        is_ok = False
    except he.Rpt_Error:
        pass
    is_ok = he.print_tests(is_ok, f'OK cannot set tag date to wrong value {is_ok}') and is_ok

    # set wrong tag type
    print()
    warning('Test wrong tag float type')
    spect = rim.read_image(spect_output)
    try:
        spect.set_metadata("injection_activity_mbq", 'tutu')
        spect.set_metadata("body_weight_kg", 'tutu')
        is_ok = False
        he.print_tests(is_ok, f'ERROR can set tag float to wrong value {is_ok}')
        print(spect.info())
    except he.Rpt_Error:
        pass
    is_ok = he.print_tests(is_ok, f'OK cannot set tag float to wrong value {is_ok}') and is_ok

    # PET
    print()
    warning('Test PET and convert to SUV')
    pet = rim.read_pet(data_folder / "spect_8.321mm.nii.gz", "Bq/mL")
    pet.body_weight_kg = 80.4
    pet.acquisition_datetime = None
    pet.injection_datetime = None
    pet.injection_activity_mbq = 7504
    pet.time_from_injection_h = 12.4
    pet.convert_to_suv()
    pet.write(output_folder / "pet.nii.gz")
    pet2 = rim.read_pet(pet.image_file_path)
    is_ok = he.are_dicts_equal(pet.to_dict(), pet2.to_dict()) and is_ok
    print(pet.info())
    he.print_tests(is_ok, f'Compare pet json')

    # end
    he.test_ok(is_ok)
