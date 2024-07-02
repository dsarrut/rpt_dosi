#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as he
from rpt_dosi.utils import start_test, stop_test, end_tests
import shutil

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001b")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # prepare image (fake one)
    im_input = data_folder / "spleen.nii.gz"
    image_path = output_folder / f"spect.nii.gz"
    shutil.copy(im_input, image_path)
    rim.delete_image_metadata(image_path)

    # test unit error
    start_test('Test if can open without unit')
    try:
        a = rim.read_spect(image_path)
        b = False
    except:
        b = True
    stop_test(b, "Cannot open without unit")

    start_test('Test if can open with unit')
    spect = rim.read_spect(image_path, unit='Bq')
    spect.write()
    spect2 = rim.read_spect(image_path)
    spect._debug_eq = True
    stop_test(spect == spect2, "Write with unit, read wo unit")

    # test unit error
    start_test('Test if wrong unit')
    try:
        spect.unit = "toto"
        b = False
    except:
        b = True
    stop_test(b, "Set wrong unit")

    try:
        spect.unit = "Bq/mL"
        b = False
    except:
        b = True
    stop_test(b, "Set unit while expect convert")

    # test unit convert
    start_test('Test convert unit and check total activity')
    t1 = spect.compute_total_activity()
    print(f'{spect} Bq --> {t1}')
    spect.convert_to_bqml()
    t2 = spect.compute_total_activity()
    print(f'{spect} BqmL --> {t2}')
    stop_test(t1 == t2, f"Total activity {t1} vs {t2}")

    # test
    start_test('Test convert_to_bq')
    spect.convert_to_bq()
    t3 = spect.compute_total_activity()
    print(f'{spect} Bq --> {t3}')
    stop_test(t1 == t3, f"Total activity {t1} vs {t3}")

    # unit SUV
    start_test('Test convert SUV')
    spect.body_weight_kg = 666
    spect.injection_activity_mbq = 33
    spect.convert_to_suv()
    t4 = spect.compute_total_activity()
    print(f'{spect} SUV --> {t4}')
    stop_test(t1 == t4, f"Total activity {t1} vs {t4}")
    print(spect.image_file_path)
    print(spect.metadata_file_path)

    # 'force' change unit
    start_test('Test FORCE convert SUV with _unit=None')
    spect._unit = None
    spect.unit = 'Bq'
    t5 = spect.compute_total_activity()
    print(f'{spect} Bq --> {t5}')
    stop_test(t1 != t5, f"Total activity {t1} must be different {t5}")

    # end
    end_tests()
