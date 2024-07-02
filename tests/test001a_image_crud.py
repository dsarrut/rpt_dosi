#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as utils
from rpt_dosi.utils import start_test, stop_test, end_tests
import shutil
import os

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = utils.get_tests_folders("test001a")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # prepare image (fake one)
    im_input = data_folder / "spleen.nii.gz"
    im_types = ['CT', 'SPECT', 'PET', 'ROI', 'Dose']
    ok = True

    # CRUD => CREATE READ UPDATE DELETE

    # test: CREATE (file exist)
    created_images = {}
    for im_type in im_types:
        start_test(f"Create an {im_type} image metadata")
        # require elements
        args = {}
        if im_type == 'SPECT':
            args = {'unit': 'Bq'}
        if im_type == 'Dose':
            args = {'unit': 'Gy'}
        if im_type == 'PET':
            args = {'unit': 'SUV'}
        if im_type == 'ROI':
            args = {'name': 'liver'}
        # create
        image_path = output_folder / f"{im_type.lower()}.nii.gz"
        shutil.copy(im_input, image_path)
        im = rim.new_metaimage(im_type, image_path, overwrite=True, **args)
        print(im)
        # write
        im.write()
        # read and compare
        im2 = rim.read_metaimage(image_path, read_header_only=True)
        im._debug_eq = True
        b = im == im2
        stop_test(b, f'Compare im1 and im2 for {im_type}')
        # ok = utils.print_tests(im == im2, f'Compare im1 and im2 for {im_type}')
        created_images[im_type] = im

    # test: CREATE (file does not exist)
    for im_type in im_types:
        start_test(f"Try to create when no image {im_type}")
        a = output_folder / f"{im_type.lower()}_fake.nii.gz"
        try:
            im = rim.new_metaimage(im_type, a)
            b = False
        except utils.Rpt_Error as e:
            b = True
        stop_test(b, f'Try to create should fail')

    # test: READ
    for im_type in im_types:
        start_test(f"Read an existing image metadata {im_type}")
        image_path = output_folder / f"{im_type.lower()}.nii.gz"
        im = rim.read_metaimage(image_path, read_header_only=True)
        print(im)
        b = created_images[im_type] == im
        stop_test(b, f'Compare im1 and im2 for {im_type}')

    # test: READ header only
    for im_type in im_types:
        start_test("Read an existing image metadata, header only")
        image_path = output_folder / f"{im_type.lower()}.nii.gz"
        im = rim.read_metaimage(image_path, read_header_only=True)
        print(im)
        b = created_images[im_type] == im
        stop_test(b, f'Compare im1 and im2 for {im_type}')

    # test: READ image (or create metadata is not exist)
    start_test("Read images")
    image_path = output_folder / f"ct.nii.gz"
    ct = rim.read_ct(image_path)
    print(ct)
    stop_test(ct.image_type == 'CT', f'read ct')

    # test
    start_test("Read images")
    image_path = output_folder / f"spect.nii.gz"
    spect = rim.read_spect(image_path, unit='Bq')
    print(spect)
    print(spect.info())
    b = spect.image_type == 'SPECT'
    stop_test(b, f'read spect')

    # test
    start_test("Read images")
    image_path = output_folder / f"roi.nii.gz"
    roi = rim.read_roi(image_path, name='liver')
    print(roi)
    b = roi.image_type == 'ROI'
    stop_test(b, f'read roi')

    # test
    start_test("Read images")
    image_path = output_folder / f"pet.nii.gz"
    pet = rim.read_pet(image_path, unit='SUV')
    print(pet)
    b = pet.image_type == 'PET'
    stop_test(b, f'read pet')

    # test
    start_test("Read images")
    image_path = output_folder / f"dose.nii.gz"
    dose = rim.read_dose(image_path)
    print(dose)
    b = dose.image_type == 'Dose'
    stop_test(b, f'read dose')

    # test: UPDATE
    start_test("Update values (spect only)")
    image_path = output_folder / f"spect.nii.gz"
    spect = rim.read_spect(image_path)
    spect.description = "toto"
    spect.body_weight_kg = 666
    spect.convert_to_bqml()
    spect.acquisition_datetime = "17 07 2009"
    spect.injection_activity_mbq = 666
    spect.injection_datetime = "2002-08-09"
    spect._debug_eq = True
    spect.write()
    spect2 = rim.read_spect(image_path)
    print(spect2)
    stop_test(spect == spect2, f'Compare updated spect')

    # test: DELETE
    start_test("Delete metadata")
    image_path = output_folder / f"roi.nii.gz"
    roi = rim.read_metaimage(image_path, read_header_only=True)
    print(roi)
    rim.delete_image_metadata(image_path)
    try:
        roi = rim.read_metaimage(image_path, read_header_only=True)
        print(roi)
        b = False
    except:
        b = True
    stop_test(not os.path.exists(roi.metadata_file_path) and b, f'Delete json')

    # test
    start_test("read image type only")
    image_path = output_folder / f"spect.nii.gz"
    it = rim.read_metaimage_type_from_metadata(image_path)
    b = it == "SPECT"
    stop_test(b, f'Read image type {it}')

    # end
    end_tests()
