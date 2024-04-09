#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.tmtv as rtmtv
import SimpleITK as sitk

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--input_filename",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Input SPECT or PET image",
)
@click.option("--threshold", "-t", default='auto', help="Threshold")
@click.option("--output", "-o", required=True, help="output filename TMTV")
@click.option("--output_mask", "-m", required=True, help="output filename TMTV mask")
def go(input_filename, threshold, output, output_mask):
    """
    input:
    - spect or pet image
    - list of rois filenames
    - thresholding

    output: new roi
    """

    # read image
    spect_image = sitk.ReadImage(input_filename)

    # default list of roi and associated dilatation in mm
    roi_list = [
        {'filename': "rois/liver.nii.gz", 'dilatation': 10},
        {'filename': "rois/kidney_left.nii.gz", 'dilatation': 10},
        {'filename': "rois/kidney_right.nii.gz", 'dilatation': 10},
        {'filename': "rois/spleen.nii.gz", 'dilatation': 10},
        {'filename': "rois/gallbladder.nii.gz", 'dilatation': 5},
        {'filename': "rois/stomach.nii.gz", 'dilatation': 5},
        {'filename': "rois/pancreas.nii.gz", 'dilatation': 5},
        {'filename': "rois/small_bowel.nii.gz", 'dilatation': 5},
        {'filename': "rois/colon.nii.gz", 'dilatation': 5},
        {'filename': "rois/duodenum.nii.gz", 'dilatation': 5},
        {'filename': "rois/urinary_bladder.nii.gz", 'dilatation': 5}
    ]

    tmtv, mask = rtmtv.tmtv_compute_mask(spect_image,
                                         "rois/skull.nii.gz",
                                         10,
                                         roi_list,
                                         threshold,
                                         verbose=True)

    # write
    sitk.WriteImage(tmtv, output)
    sitk.WriteImage(mask, output_mask)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
