#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as he
from rpt_dosi.utils import warning
import shutil
import os

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001a")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # prepare image (fake one)
    im_input = data_folder / "spleen.nii.gz"
    im_types = ['CT', 'SPECT', 'PET', 'ROI', 'Dose']
    ok = True

    # CRUD => CREATE READ UPDATE DELETE

    # test: CREATE (file exist)
    print()
    warning("Create an image metadata")
    created_images = {}
    for im_type in im_types:
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
        ok = he.print_tests(im == im2, f'Compare im1 and im2 for {im_type}') and ok
        created_images[im_type] = im

    # test: CREATE (file does not exist)
    print()
    warning("Try to create when no image")
    for im_type in im_types:
        a = output_folder / f"{im_type.lower()}_fake.nii.gz"
        try:
            im = rim.new_metaimage(im_type, a)
            ok = False
        except he.Rpt_Error as e:
            pass
    he.print_tests(ok, f'Try to create should fail')

    # test: READ
    print()
    warning("Read an existing image metadata")
    for im_type in im_types:
        image_path = output_folder / f"{im_type.lower()}.nii.gz"
        im = rim.read_metaimage(image_path, read_header_only=True)
        print(im)
        ok = he.print_tests(created_images[im_type] == im, f'Compare im1 and im2 for {im_type}') and ok

    # test: READ header only
    print()
    warning("Read an existing image metadata, header only")
    for im_type in im_types:
        image_path = output_folder / f"{im_type.lower()}.nii.gz"
        im = rim.read_metaimage(image_path, read_header_only=True)
        print(im)
        ok = he.print_tests(created_images[im_type] == im, f'Compare im1 and im2 for {im_type}') and ok

    # test: READ image (or create metadata is not exist)
    print()
    warning("Read images")
    image_path = output_folder / f"ct.nii.gz"
    ct = rim.read_ct(image_path)
    print(ct)
    ok = he.print_tests(ct.image_type == 'CT', f'read ct') and ok

    image_path = output_folder / f"spect.nii.gz"
    spect = rim.read_spect(image_path, unit='Bq')
    print(spect)
    print(spect.info())
    ok = he.print_tests(spect.image_type == 'SPECT', f'read spect') and ok

    image_path = output_folder / f"roi.nii.gz"
    roi = rim.read_roi(image_path, name='liver')
    print(roi)
    ok = he.print_tests(roi.image_type == 'ROI', f'read roi') and ok

    image_path = output_folder / f"pet.nii.gz"
    pet = rim.read_pet(image_path, unit='SUV')
    print(pet)
    ok = he.print_tests(pet.image_type == 'PET', f'read pet') and ok

    image_path = output_folder / f"dose.nii.gz"
    dose = rim.read_dose(image_path)
    print(dose)
    ok = he.print_tests(dose.image_type == 'Dose', f'read dose') and ok

    # test: UPDATE
    print()
    warning("Update values (spect only)")
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
    ok = he.print_tests(spect == spect2, f'Compare updated spect') and ok

    # test: DELETE
    print()
    warning("Delete metadata")
    image_path = output_folder / f"roi.nii.gz"
    roi = rim.read_metaimage(image_path, read_header_only=True)
    print(roi)
    rim.delete_image_metadata(image_path)
    try:
        roi = rim.read_metaimage(image_path, read_header_only=True)
        print(roi)
        ok = False
    except:
        pass
    ok = he.print_tests(not os.path.exists(roi.metadata_file_path), f'Delete json') and ok

    # test
    print()
    warning("read image type only")
    image_path = output_folder / f"spect.nii.gz"
    it = rim.read_metaimage_type_from_metadata(image_path)
    b = it == "SPECT"
    ok = he.print_tests(b, f'Read image type {it}') and ok

    # end
    he.test_ok(ok)
