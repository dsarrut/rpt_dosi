#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.helpers as he
import rpt_dosi.tmtv as rtmtv
import rpt_dosi.images as rim
import SimpleITK as sitk

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test006")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # test 3 with gafita2019 threshold
    print()
    print()
    print("TMTV (auto threshold)")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    output = output_folder / "tmtv_auto.nii.gz"
    output_mask = output_folder / "tmtv_mask_auto.nii.gz"
    tmtv_extractor = rtmtv.TMTV()
    tmtv_extractor.intensity_threshold = "gafita2019"
    tmtv_extractor.verbose = True
    tmtv_extractor.cut_the_head = True
    tmtv_extractor.cut_the_head_roi_filename = data_folder / "rois/skull.nii.gz"
    tmtv_extractor.rois_to_remove_folder = data_folder / "rois"
    # (pop mean liver computed to get the same results as the previous test)
    tmtv_extractor.population_mean_liver = 10993.43824370773
    tmtv_extractor.minimal_volume_cc = 2
    spect = sitk.ReadImage(spect_input)

    # go
    tmtv, mask = tmtv_extractor.compute_mask(spect)
    sitk.WriteImage(mask, output_mask)
    sitk.WriteImage(tmtv, output)

    # compare
    tmtv_ref = ref_folder / "tmtv_ref_auto_min_cc.nii.gz"
    b = rim.test_compare_images(output, tmtv_ref)
    he.print_tests(b, f"Compare TMTV {output} vs {tmtv_ref}")
    is_ok = b

    # compare
    tmtv_ref = ref_folder / "tmtv_mask_ref_auto_min_cc.nii.gz"
    b = rim.test_compare_images(output_mask, tmtv_ref)
    he.print_tests(b, f"Compare TMTV mask {output_mask} vs {tmtv_ref}")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
