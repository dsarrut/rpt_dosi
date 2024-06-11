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

    # test
    # rpt_tmtv -i spect_8.321mm.nii.gz -o test006/tmtv_ref.nii.gz -m test006/tmtv_mask_ref.nii.gz -t 100000
    print("TMTV (simple version)")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    output = output_folder / "tmtv.nii.gz"
    output_mask = output_folder / "tmtv_mask.nii.gz"
    cmd = f"rpt_tmtv -i {spect_input} -o {output} -m {output_mask} -t 100000"
    is_ok = he.run_cmd(cmd, data_folder)

    # compare
    tmtv_ref = ref_folder / "tmtv_ref.nii.gz"
    b = rim.test_compare_images(output, tmtv_ref)
    he.print_tests(b, f"Compare TMTV {output} vs {tmtv_ref}")
    is_ok = b and is_ok

    # compare
    tmtv_ref = ref_folder / "tmtv_mask_ref.nii.gz"
    b = rim.test_compare_images(output_mask, tmtv_ref)
    he.print_tests(b, f"Compare TMTV mask {output_mask} vs {tmtv_ref}")
    is_ok = b and is_ok

    # test 2 with automated threshold
    # rpt_tmtv -i data/spect_8.321mm.nii.gz -o data/test006/tmtv_ref_auto.nii.gz
    # -m data/test006/tmtv_mask_ref_auto.nii.gz -t auto
    print()
    print()
    print("TMTV (auto threshold)")
    spect_input = data_folder / "spect_8.321mm.nii.gz"
    output = output_folder / "tmtv_auto.nii.gz"
    output_mask = output_folder / "tmtv_mask_auto.nii.gz"
    tmtv_extractor = rtmtv.TMTV()
    tmtv_extractor.intensity_threshold = "auto"
    tmtv_extractor.verbose = True
    tmtv_extractor.cut_the_head = True
    tmtv_extractor.cut_the_head_roi_filename = data_folder / "rois/skull.nii.gz"
    tmtv_extractor.rois_to_remove_folder = data_folder / "rois"
    spect = sitk.ReadImage(spect_input)
    tmtv, mask = tmtv_extractor.compute_mask(spect)
    sitk.WriteImage(mask, output_mask)
    sitk.WriteImage(tmtv, output)

    # compare
    tmtv_ref = ref_folder / "tmtv_ref_auto.nii.gz"
    b = rim.test_compare_images(output, tmtv_ref)
    he.print_tests(b, f"Compare TMTV {output} vs {tmtv_ref}")
    is_ok = b and is_ok

    # compare
    tmtv_ref = ref_folder / "tmtv_mask_ref_auto.nii.gz"
    b = rim.test_compare_images(output_mask, tmtv_ref)
    he.print_tests(b, f"Compare TMTV mask {output_mask} vs {tmtv_ref}")
    is_ok = b and is_ok

    # end
    he.test_ok(is_ok)
