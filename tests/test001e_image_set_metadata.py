#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as he
from rpt_dosi.utils import start_test, stop_test, end_tests
import math
import shutil
import json

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001e")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # prepare
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_activity.nii.gz"
    rim.delete_image_metadata(spect_output)
    spect = rim.read_spect(spect_input, 'Bq')
    spect.write(spect_output)

    # test
    start_test(f'set metadata from cmd line')
    cmd = f"rpt_image_set_metadata -i {spect_output} --tag injection_activity_mbq 7400 --tag body_weight_kg 80"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, f'cmd')
    sp = rim.read_spect(spect_output)
    print(sp)
    b = sp.injection_activity_mbq == 7400
    stop_test(b, f'Test injection activity mbq = {b}')
    b = sp.body_weight_kg == 80
    stop_test(b, f'Test body_weight_kg = {b}')
    sp.write()
    t1 = sp.compute_total_activity()

    # test
    print()
    start_test(f'set metadata from cmd line')
    cmd = f"rpt_image_set_metadata -i {spect_output} --unit SUV --tag description toto"
    b = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, f'cmd')
    sp = rim.read_spect(spect_output)
    t2 = sp.compute_total_activity()
    b = math.isclose(t1, t2, rel_tol=1e-6)
    stop_test(b, f'Compare total activity {t1} and {t2}')

    # test
    # set meta unit Bq
    start_test('Test command line rpt_image_set_metadata with spect')
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    spect_output = output_folder / "spect_8.321mm.nii.gz"
    shutil.copy(spect_input, spect_output)
    rim.delete_image_metadata(spect_output)
    cmd = f"rpt_image_set_metadata -i {spect_output} -u Bq -t SPECT"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(b, f'cmd')
    out_spect = rim.read_spect(spect_output)
    b = out_spect.image_type == 'SPECT' and out_spect.unit == 'Bq'
    stop_test(b, f'(read spect) Set metadata read SPECT and Bq ?')

    # set meta again with already existing metadata
    start_test('Test read_image')
    spect = rim.read_metaimage(spect_output)
    try:
        spect.unit = 'Bq/mL'
    except:
        b = True
    stop_test(b, f'OK cannot set unit because already there')
    b = spect.image_type == 'SPECT' and spect.unit == 'Bq'
    stop_test(b, f'(read image) Set metadata read SPECT and Bq ?')

    # check filename in the json file
    start_test('Test metadata json file')
    fn = spect.metadata_file_path
    with open(fn, 'r') as f:
        data = json.load(f)
        data['filename'] = "titi.nii.gz"
    with open(fn, 'w') as f:
        json.dump(data, f)
    try:
        spect = rim.read_metaimage(spect_output)
        b = False
    except:
        b = True
    stop_test(b, f'OK cannot read with wrong filename tag')

    # check wrong but existing json file
    start_test('check wrong but existing json file')
    open(fn, 'w').close()
    try:
        spect = rim.read_metaimage(spect_output)
        b = False
    except:
        b = True
    stop_test(b, f'OK cannot read wrong file')

    # set meta unit Bq/mL
    start_test('Test set unit with rpt_image_set_metadata')
    cmd = f"rpt_image_set_metadata -i {spect_output} -u Bq/mL -t SPECT -f"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(cmd_ok, f'cmd')
    out_spect = rim.read_spect(spect_output)
    b = out_spect.image_type == 'SPECT' and out_spect.unit == 'Bq/mL' and cmd_ok
    stop_test(b, f'(read spect) Set metadata read SPECT and Bq/mL ?')

    # set for a roi
    start_test('Test set roi info')
    cmd = f"rpt_image_set_metadata -i {spect_output} --tag name liver -t ROI -f"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(cmd_ok, f'cmd')
    out_roi = rim.read_roi(spect_output)
    b = out_roi.image_type == 'ROI' and out_roi.name == 'liver' and cmd_ok
    stop_test(b, f'(read roi) Set metadata read ROI and liver ?')

    # set for a roi wo name
    start_test('Test set roi without name')
    cmd = f"rpt_image_set_metadata -i {spect_output} -t ROI -f"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(not cmd_ok, f'cmd')

    # set for a roi wo name
    start_test('Test set roi wrong unit')
    cmd = f"rpt_image_set_metadata -i {spect_output} --name liver -u Bq -t ROI -f"
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(not cmd_ok, f'cmd')

    # set tags for spect
    rim.delete_image_metadata(spect_output)
    spect = rim.read_spect(spect_output, unit='Bq')
    spect.write_metadata()
    start_test('Test set tags rpt_image_set_metadata')
    cmd = (f'rpt_image_set_metadata -i {spect_output}'
           f' --tag injection_datetime "2022-02-01 12:11:00"'
           f' --tag injection_activity_mbq 7504'
           f' --tag acquisition_datetime "2022-02-01 18:11:00"'
           f' --tag body_weight_kg 70.4 -v')
    cmd_ok = he.run_cmd(cmd, data_folder / "..")
    stop_test(cmd_ok, f'cmd')

    # special case for time_from_injection_h
    start_test('Test acquisition_datetime')
    spect = rim.read_metaimage(spect_output)
    spect.body_weight_kg = 80.4
    spect.acquisition_datetime = None
    spect.injection_datetime = None
    spect.time_from_injection_h = 12.4
    print(spect.acquisition_datetime)
    b = spect.acquisition_datetime == "1970-01-01 12:24:00" and cmd_ok
    stop_test(b, f'correct date ? {b}')

    # special case for time_from_injection_h
    start_test('Test time_from_injection_h')
    spect = rim.read_metaimage(spect_output)
    try:
        spect.time_from_injection_h = 12.4
        b = False
    except:
        b = True
    stop_test(b, f'Can set time from injection tag')

    # set wrong tag
    start_test('Test wrong metadata')
    spect = rim.read_metaimage(spect_output)
    try:
        spect.set_metadata("toto", 'titi')
        b = False
    except:
        b = True
    stop_test(b, f'OK cannot set wrong tag')

    # set wrong tag
    start_test('Test wrong tag date type')
    ct_input = data_folder / "ct_8mm.nii.gz"
    ct = rim.read_ct(ct_input)
    try:
        ct.set_metadata("injection_datetime", 'titi')
        b = False
    except:
        b = True
    stop_test(b, f'OK cannot set tag date to wrong value')

    # set wrong tag type
    start_test('Test wrong tag float type')
    spect = rim.read_metaimage(spect_output)
    try:
        spect.set_metadata("injection_activity_mbq", 'tutu')
        spect.set_metadata("body_weight_kg", 'tutu')
        b = False
        print(spect.info())
    except:
        b = True
    stop_test(b, f'OK cannot set tag float to wrong value')

    # PET
    start_test('Test PET and convert to SUV')
    rim.delete_image_metadata(spect_output)
    pet = rim.read_pet(spect_output, "Bq/mL")
    pet.body_weight_kg = 80.4
    pet.acquisition_datetime = None
    pet.injection_datetime = None
    pet.injection_activity_mbq = 7504
    pet.time_from_injection_h = 12.4
    pet.convert_to_suv()
    pet.write(output_folder / "pet.nii.gz")
    pet2 = rim.read_pet(pet.image_file_path)
    b = he.are_dicts_float_equal(pet.to_dict(), pet2.to_dict())
    print(pet.info())
    stop_test(b, f'Compare pet json')

    # end
    end_tests()
