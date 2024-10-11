#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import click
import rpt_dosi.doserate as dora
import opengate as gate
from rpt_dosi.images import read_dose, read_metaimage

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--spect",
    "-s",
    required=True,
    type=click.Path(exists=True),
    help="Input SPECT in Bq",
)
@click.option(
    "--ct",
    "-c",
    required=True,
    type=click.Path(exists=True),
    help="Input CT image",
)
@click.option("--output_folder", "-o", required=True, help="Output folder for results")
@click.option("--rad", default="lu177", help="Radionuclide")
@click.option("--resample_like", "-r",
              default="spect",
              help="Resample images like 'spect', 'ct' or give a voxel size in mm")
@click.option("--sigma", default="auto",
              help="specify sigma for gauss filter (None=no gauss, 0 = auto)",
              )
@click.option("--activity_bq", "-a", default=1e4, help="Activity in Bq")
@click.option("--number_of_threads", "-t", default=1, help="Threads")
def go(spect, ct, rad, resample_like, output_folder, sigma, activity_bq, number_of_threads):

    # output folder
    os.makedirs(output_folder, exist_ok=True)

    # init the simulation object
    s = dora.DoseRateSimulation(ct, spect)
    s.resample_like = resample_like
    s.radionuclide = rad
    s.output_folder = output_folder
    s.gaussian_sigma = sigma
    s.activity_bq = activity_bq

    # create the GATE simulation
    sim = gate.Simulation()
    source = s.init_gate_simulation(sim)

    # adapt multithreading
    sim.number_of_threads = number_of_threads
    source.activity = source.activity / sim.number_of_threads

    # compute the scaling factor
    scaling = s.compute_scaling(sim, 'Bq')

    # go
    sim.run()

    # print results at the end
    stats = sim.get_actor("stats")
    print(stats)
    print(f'Total activity scaling factor is {scaling}')

    # add metadata to the output
    da = sim.get_actor("dose")
    dr = read_dose(da.dose.get_output_path(), unit="Gy/s")
    spect_im = read_metaimage(spect)
    dr.injection_datetime = spect_im.injection_datetime
    dr.acquisition_datetime = spect_im.acquisition_datetime
    dr.image = dr.image * scaling
    dr.write()
    print(dr)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
