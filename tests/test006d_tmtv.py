#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

import rpt_dosi.utils as he
import rpt_dosi.tmtv as rtmtv
import rpt_dosi.images as rim
import SimpleITK as sitk
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test006d")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # test 3 with gafita2019 threshold
    start_test("TMTV with rois to keep")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    output = output_folder / "tmtv_auto.nii.gz"
    output_mask = output_folder / "tmtv_mask_auto.nii.gz"
    tmtv_extractor = rtmtv.TMTV()
    tmtv_extractor.intensity_threshold = 5000
    tmtv_extractor.verbose = True
    tmtv_extractor.cut_the_head = True
    tmtv_extractor.cut_the_head_roi_filename = data_folder / "rois/skull.nii.gz"
    tmtv_extractor.rois_to_remove_folder = data_folder / "rois"
    tmtv_extractor.rois_to_keep_folder = data_folder / "rois"
    tmtv_extractor.rois_to_remove = [
        {"filename": "liver.nii.gz", "dilatation": 50},
        {"filename": "kidney_left.nii.gz", "dilatation": 0},
        {"filename": "spleen.nii.gz", "dilatation": 0},
    ]
    f = data_folder / "test006d" / "test006_rois_to_keep.json"
    with open(f, "r") as f:
        rois_to_keep = json.load(f)
    tmtv_extractor.rois_to_keep = rois_to_keep
    spect = sitk.ReadImage(spect_input)

    # go
    tmtv, mask = tmtv_extractor.compute_mask(spect)
    sitk.WriteImage(mask, output_mask)
    sitk.WriteImage(tmtv, output)

    print("done", output, output_mask)

    # compare
    tmtv_ref = ref_folder / "tmtv_auto.nii.gz"
    b = rim.test_compare_images(output, tmtv_ref)
    stop_test(b, f"Compare TMTV {output} vs {tmtv_ref}")

    # compare
    tmtv_ref = ref_folder / "tmtv_mask_auto.nii.gz"
    b = rim.test_compare_images(output_mask, tmtv_ref)
    stop_test(b, f"Compare TMTV mask {output_mask} vs {tmtv_ref}")

    # end
    end_tests()
