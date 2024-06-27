#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import SimpleITK

import rpt_dosi.images as rim
import rpt_dosi.helpers as he
from rpt_dosi.helpers import warning
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
    rim.delete_metadata(image_path)
    ok = True

    # test unit error
    print()
    warning('Test if can open without unit')
    try:
        a = rim.read_spect(image_path)
        ok = False
    except:
        he.print_tests(ok, "Cannot open without unit")
    spect = rim.read_spect(image_path, input_unit='Bq')
    spect.write()
    spect2 = rim.read_spect(image_path)
    spect._debug_eq = True
    ok = he.print_tests(spect == spect2, "Write with unit, read wo unit") and ok

    # test unit error
    print()
    warning('Test if wrong unit')
    try:
        spect.unit = "toto"
        ok = False
    except:
        pass
    he.print_tests(ok, "Set wrong unit")

    try:
        spect.unit = "Bq/mL"
        ok = False
    except:
        pass
    he.print_tests(ok, "Set unit while expect convert")

    # test unit convert
    print()
    warning('Test convert unit and check total activity')
    t1 = spect.compute_total_activity()
    print(f'{spect} Bq --> {t1}')
    spect.convert_to_bqml()
    t2 = spect.compute_total_activity()
    print(f'{spect} BqmL --> {t2}')
    ok = he.print_tests(t1 == t2, f"Total activity {t1} vs {t2}") and ok
    spect.convert_to_bq()
    t3 = spect.compute_total_activity()
    print(f'{spect} Bq --> {t3}')
    ok = he.print_tests(t1 == t3, f"Total activity {t1} vs {t3}") and ok

    # unit SUV
    print()
    warning('Test convert SUV')
    spect.body_weight_kg = 666
    spect.injection_activity_mbq = 33
    spect.convert_to_suv()
    t4 = spect.compute_total_activity()
    print(f'{spect} SUV --> {t4}')
    ok = he.print_tests(t1 == t4, f"Total activity {t1} vs {t4}") and ok
    print(spect.image_file_path)
    print(spect.metadata_file_path)

    # 'force' change unit
    print()
    warning('Test FORCE convert SUV with _unit=None')
    spect._unit = None
    spect.unit = 'Bq'
    t5 = spect.compute_total_activity()
    print(f'{spect} Bq --> {t5}')
    ok = he.print_tests(t1 != t5, f"Total activity {t1} must be different {t5}") and ok

    # end
    he.test_ok(ok)
