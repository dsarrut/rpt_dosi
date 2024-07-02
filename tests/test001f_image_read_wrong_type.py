#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.images as rim
import rpt_dosi.utils as he
from rpt_dosi.utils import warning
import shutil

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test001f")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # test
    print()
    warning('Update image with no metadata, add CT metadata (cmd line)')
    filename = "ct_8mm.nii.gz"
    ct_input = data_folder / filename
    ct_output = output_folder / filename
    shutil.copy(ct_input, ct_output)
    rim.delete_image_metadata(ct_output)
    cmd = f"rpt_image_set_metadata -i {ct_output} -t CT -v"
    is_ok = he.run_cmd(cmd, data_folder / "..")
    he.print_tests(is_ok, f'cmd line {is_ok}')

    # test
    print()
    warning('Read image with metadata (CT)')
    im = rim.read_ct(ct_output)
    print(im.metadata_file_path)
    with open(im.metadata_file_path) as f:
        print(f.read())
    b = im.image_type == 'CT' and im.unit == 'HU'
    he.print_tests(b, f'image metadata is CT and HU {im}: {b}')
    is_ok = b and is_ok

    # test
    print()
    warning('Read image with no metadata, consider as spect (function), no unit')
    rim.delete_image_metadata(ct_output)
    im = rim.read_spect(ct_output, "Bq")
    im.write_metadata()
    b = im.image_type == 'SPECT' and im.unit == "Bq" and is_ok
    he.print_tests(b, f'result = {im} : {b}')
    is_ok = b and is_ok

    # Read image with wrong type
    print()
    warning('Read image with wrong type (expect exception)')
    try:
        im = rim.read_ct(ct_output)
        print(im)
        b = False
    except he.Rpt_Error:
        b = True
    he.print_tests(b, f"Cannot read SPECT as CT : {b}")
    is_ok = b and is_ok

    # Read image with wrong type
    print()
    warning('Read image with wrong type')
    b = False
    try:
        im = rim.read_roi(ct_output, 'toto')
    except he.Rpt_Error:
        b = True
    he.print_tests(b, f"Cannot read SPECT as ROI : {b}")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
