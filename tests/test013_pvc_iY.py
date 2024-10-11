#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import SimpleITK as sitk
import rpt_dosi.utils as he
import rpt_dosi.images as rim
from rpt_dosi.utils import start_test, stop_test

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test013")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    # cpp command line
    # ./petpvc -i data/test013/spect_rescaled.nii.gz -o data/test013/spect_corrected.nii.gz
    # -p IY -x 10 -y 10 -z 10 -m data/test013/left_kidney_resampled.nii.gz -n 3 -debug

    # read spect image
    start_test("Compute iY PVC")
    spect = rim.read_spect(ref_folder / "spect_rescaled.nii.gz", "Bq")
    print(spect)

    # read one single mask
    mask = rim.read_roi(ref_folder / "left_kidney_resampled.nii.gz", "left_kidney")
    print(mask)

    # set ref image bg
    '''im = sitk.ReadImage(ref_folder / 'spect_corrected.nii.gz')
    arr = sitk.GetArrayFromImage(im)
    m = sitk.GetArrayViewFromImage(mask.image)
    arr[m!=1] = 0
    o = sitk.GetImageFromArray(arr)
    o.CopyInformation(im)
    sitk.WriteImage(o, ref_folder / 'spect_corrected.nii.gz')'''

    # apply PVC with iY
    f = rim.PVCIterativeYang()
    f.input_image = spect.image
    f.mask = mask.image
    f.fwhm_mm = [10, 10, 10]
    f.verbose = True
    f.run()

    # dump (not needed)
    n = output_folder / "pvc_iy.nii.gz"
    sitk.WriteImage(f.output, n)

    # compare images
    r = ref_folder / 'spect_corrected.nii.gz'
    is_ok = rim.test_compare_images(n, r)
    stop_test(is_ok, f"Compare iY images {n} vs {r}")

    # end
    he.test_ok(is_ok)
