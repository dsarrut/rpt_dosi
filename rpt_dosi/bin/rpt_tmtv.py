#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import json
import rpt_dosi.tmtv as rtmtv
import rpt_dosi.images as rim
import rpt_dosi.utils as ru
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
@click.option("--threshold", "-t", default='auto', help="Threshold method (float or 'auto', or 'gafita2019'")
@click.option("--population_mean_liver", default=None, help="Used with 'gafita2019' thresholding method")
@click.option("--minimal_volume_cc", default=None, help="Remove areas less than minimal_volume_cc")
@click.option("--roi_list", default=None, help="Json file with physiological roi filename and dilatation (to remove)")
@click.option("--skull", default=None, help="Skull roi (to remove head)")
@click.option("--output", "-o", required=True, help="output filename TMTV")
@click.option("--output_mask", "-m", required=True, help="output filename TMTV mask")
@click.option("--verbose", "-v", is_flag=True, default=False, help="verbose")
def go(input_filename,
       threshold, output, output_mask,
       roi_list, population_mean_liver,
       skull,
       minimal_volume_cc,
       verbose):
    """
    Compute TMTV Total Metabolic Tumor Volume
    input:
    - spect or pet image
    - list of rois filenames
    - thresholding
    output: new roi mask and TMTV
    """

    # read image (SPECT or PET)
    try:
        image = rim.read_spect(input_filename, unit='Bq')
    except:
        image = rim.read_pet(input_filename, unit='Bq/mL')

    # user defined list of roi and associated dilatation in mm
    # JSON file must be a list of {'filename': "liver.nii.gz", 'dilatation': 10}
    if roi_list is not None:
        with open(roi_list, 'r') as file:
            roi_list = json.load(file)

    # create main object and set options
    tmtv_extractor = rtmtv.TMTV()
    tmtv_extractor.intensity_threshold = threshold
    if roi_list is not None:
        tmtv_extractor.rois_to_remove = roi_list
    tmtv_extractor.verbose = True
    tmtv_extractor.cut_the_head = True
    tmtv_extractor.cut_the_head_margin_mm = 10
    tmtv_extractor.cut_the_head_roi_filename = skull
    tmtv_extractor.population_mean_liver = population_mean_liver
    tmtv_extractor.minimal_volume_cc = minimal_volume_cc

    # go
    verbose and print(f'Input image \n{image.info()}')
    tmtv, mask = tmtv_extractor.compute_mask(image.image)

    # convert to image type for input image (if any)
    sitk.WriteImage(tmtv, output)
    tmtv_img = rim.new_metaimage(image.image_type, output, unit=image.unit)
    tmtv_img.image = tmtv
    tmtv_img.write_metadata()

    # convert to image type for mask
    sitk.WriteImage(mask, output_mask)
    roi_img = rim.MetaImageROI(output_mask, reading_mode='image', create=True, name='tmtv')
    roi_img.image = mask
    roi_img.write_metadata()
    verbose and print(f'Output tmtv {output}')
    verbose and print(f'Output mask {output_mask}')


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
