#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.opendose as od
import json

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--phantom", "-p", default="ICRP 110 AM", help="Phantom ICRP 110 AF or AM"
)
@click.option(
    "--source", "-s", default="liver", help="Name of the source: liver, kidney, etc"
)
@click.option("--rad", "-r", default="lu177", help="Name of isotope")
@click.option(
    "--output", "-o", required=True, default="auto", help="output filename (json)"
)
def go(phantom, source, rad, output):
    # get ids
    ph_id, phantom = od.guess_phantom_id(phantom)
    print(f"Phantom id: {ph_id} = {phantom}")

    source_id, source_name = od.guess_source_id(phantom, source)
    print(f"Source id: {source_id} = {source_name}")

    isotope_id, isotope_name = od.guess_isotope_id(phantom, rad)
    print(f"Isotope id: {isotope_id} = {isotope_name}")

    # query the site for the file
    print(f"Connecting to the opendose site https://opendose.org/svalues ...")
    driver, model_dropdown = od.web_svalues_get_driver()
    print(f"Select the phantom {phantom} ...")
    od.web_svalues_select_phantom(driver, model_dropdown, ph_id)
    print(f"Query the {rad} svalues for {source} ...")
    data = od.web_svalues_query_data(driver, source_id, isotope_id)

    # auto output ?
    if output == "auto":
        output = od.get_svalue_data_filename(phantom, source_name, isotope_name)

    # write to json file
    print(f"Save the data in {output}")
    with open(output, "w") as f:
        json.dump(data, f, indent=4)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
