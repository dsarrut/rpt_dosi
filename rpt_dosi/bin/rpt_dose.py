#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import click
from rpt_dosi import dosimetry as rd
import rpt_dosi.images as rim

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--spect",
    "-s",
    default=None,
    type=click.Path(exists=True),
    help="Input SPECT image (use --unit to specify the image)",
)
@click.option(
    "--dose_rate",
    "-d",
    default=None,
    type=click.Path(exists=True),
    help="Input dose rate image",
)
@click.option("--input_unit", "-u",
              type=click.Choice(rim.ImageSPECT.authorized_units + ['Gy/s']),
              default=None,
              help=f"SPECT or dose rate unit: {rim.ImageSPECT.authorized_units + ['Gy/s']}")
@click.option(
    "--ct",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Input CT image",
)
@click.option(
    "--roi_list", "-l", type=str, default=None, help="Filename : list of ROI filename and name"
)
@click.option(
    "--roi", "-r", multiple=True, type=(str, str, float), help="ROI: filename + name + Teff"
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
@click.option("--output", "-o", default=None, help="Output json filename")
def go(spect,
       dose_rate,
       ct,
       input_unit,
       time_from_injection_h,
       phantom,
       rad,
       resample_like,
       roi_list,
       roi,
       sigma,
       output,
       method,
       scaling):
    # spect or dose_rate ?
    if spect is None and dose_rate is None:
        rim.fatal(f'Please provide either --spect or --dose_rate option')
    if spect is not None and dose_rate is not None:
        rim.fatal('Please provide either --spect or --dose_rate option, not both')

    # read spect
    im = None
    if spect is not None:
        im = rim.read_spect(spect, input_unit)

    # read dose_rate
    if dose_rate is not None:
        im = rim.read_dose(dose_rate, input_unit)
        print(im.unit)
        if im.unit != "Gy/s":
            rim.fatal("Dose rate pixel type must be 'Gy/s'")

    # timing (read in sidecar metadata or option)
    if time_from_injection_h is None:
        if im.time_from_injection_h is None:
            rim.fatal('Please provide --time_from_injection_h')
    else:
        im.time_from_injection_h = time_from_injection_h

    # read rois
    if roi_list is not None:
        rois = rim.read_list_of_rois(roi_list)
    else:
        rois = []
    for r in roi:
        a_roi = rim.read_roi(r[0], r[1], r[2])
        rois.append(a_roi)

    # read ct image
    ct = rim.read_ct(ct)

    # create the dose method
    the_method = rd.get_dose_computation_class(method)
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

    # save output to json
    if output is not None:
        with open(output, "w") as f:
            json.dump(doses, f, indent=4)
            print(f'Results saved in {output}')

    # print
    for d in doses:
        print(f'{d} = {doses[d]}')


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
