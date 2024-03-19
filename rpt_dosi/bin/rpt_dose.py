#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import click
from rpt_dosi import dosimetry as rd
import rpt_dosi.images as rim

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--input_image",
    "-s",
    required=True,
    type=click.Path(exists=True),
    help="Input SPECT or dose_rate image (use --unit to specify the image)",
)
@click.option("--input_unit", "-u",
              type=click.Choice(rim.ImageSPECT.authorized_units + ['Gy_sec']),
              required=True,
              help=f"SPECT unit: {rim.ImageSPECT.authorized_units}")
@click.option(
    "--ct",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Input CT image",
)
@click.option("--output", "-o", required=True, help="Output json filename")
@click.option(
    "--roi_list", "-l", type=str, help="Filename : list of ROI filename and name"
)
@click.option("--time_from_injection_h", "-t", type=float, required=True, help="Time in h")
@click.option("--rad", default="lu177", help="Radionuclide")
@click.option(
    "--method",
    "-m",
    default="hanscheid2017",
    type=click.Choice(["hanscheid2017",
                       "hanscheid2018",
                       "madsen2018",
                       "madsen2018_dose_rate"]),
    help="Which method to use",
)
@click.option("--resample_like", "-r",
              type=click.Choice(["spect", "ct"]),
              default="spect",
              help="Resample image like spect, dose_rate or ct")
@click.option("--sigma", default="auto",
              help="specify sigma for gauss filter (None=no gauss, 0 = auto)",
              )
@click.option(
    "--phantom", "-p", default="ICRP 110 AM", help="Phantom ICRP 110 AF or AM (only used by some methods)"
)
@click.option("--scaling", default=1.0, help="Scaling factor (for dose rate)")
def go(input_image, ct, input_unit, time_from_injection_h,
       phantom, rad, resample_like,
       roi_list, sigma, output, method, scaling):
    # read ct image
    ct = rim.read_ct(ct)

    # read spect or dose_rate
    im = rim.read_image(input_image)
    if im.image_type is None:
        if input_unit is None:
            raise ValueError("Unknown image type, please set --input_unit")
        if input_unit == "Gy/sec":
            im = rim.read_dose(input_image, input_unit)
        else:
            im = rim.read_spect(input_image, input_unit)
    im.time_from_injection_h = time_from_injection_h

    # read rois
    rois = rim.read_list_of_rois(roi_list)

    # create the dose method
    the_method = rd.get_dose_computation_method(method)
    d = the_method(ct, im)

    # common options
    d.resample_like = resample_like
    d.radionuclide = rad
    d.gaussian_sigma = sigma

    # specific options (only used by some methods)
    d.phantom = phantom
    d.scaling = scaling

    # compute dose for all roi
    doses = d.run(rois)

    # save output to json and print
    with open(output, "w") as f:
        json.dump(doses, f, indent=4)

    # print
    for d in doses:
        print(f'{d} = {doses[d]}')
    print(f'Results saved in {output}')


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
