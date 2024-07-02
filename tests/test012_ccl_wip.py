#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as he
import rpt_dosi.tmtv as rtmtv
import rpt_dosi.dosimetry as rd
import rpt_dosi.images as rim
import os
import numpy as np
from pathlib import Path
import SimpleITK as sitk

if __name__ == "__main__":
    # folders
    '''data_folder, ref_folder, output_folder = he.get_tests_folders("test011")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()'''

    # test
    # spect_input = data_folder / "spect_8.321mm.nii.gz"
    output_folder = Path("/Users/dsarrut/src/py/rpt_dosi/rpt_dosi/patient_test/cycle1/tp2")
    spect_filename = output_folder / "spect.nii.gz"
    tmtv_filename = output_folder / "tmtv.nii.gz"
    tmtv_mask_filename = output_folder / "tmtv_mask.nii.gz"
    landmarks_file = output_folder / "landmarks.txt"

    # ccl
    tmtv = rim.read_spect(tmtv_filename, 'Bq')
    tmtv_mask = rim.read_roi(tmtv_mask_filename, 'tmtv')
    label_img = rtmtv.find_foci(tmtv, tmtv_mask, min_size_cm3=1, percentage_threshold=0.001)

    # (todo : convert sitk to rpt image)

    # write labels image
    sitk.WriteImage(label_img, output_folder / "label_img.nii.gz")

    # get the centroids
    foci_centroids = rtmtv.get_label_centroids(label_img)
    for centroid in foci_centroids:
        print(centroid)

    # write landmarks file for vv
    with open(landmarks_file, 'w') as f:
        f.write("LANDMARKS1")
        i = 0
        for centroid in foci_centroids:
            f.write(f"{i} {centroid[0]} {centroid[1]} {centroid[2]} 0 0\n")
            i = i + 1
