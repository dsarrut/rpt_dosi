#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.dicom_utils as dicom
import json
import questionary
from box import Box
import os

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--dicom_json", "-i", required=True, help="Input DICOM DIR json")
@click.option("--output", "-o", required=True, help="Output json file with dicom info")
@click.option("--filter", "-f", is_flag=True, help="Filter NM only")
@click.option(
    "--filter_desc",
    "-d",
    multiple=True,
    help="Filter NM description that contains this txt",
)
def go(dicom_json, filter, filter_desc, output):
    # load the dicom info
    with open(dicom_json, "r") as f:
        studies = json.load(f)

    # filters study with NM only
    if filter:
        studies = dicom.filter_studies_include_modality(studies, "NM")

    # filters series: remove OT
    if filter:
        studies = dicom.filter_series_rm_modality(studies, "OT")
        studies = dicom.filter_series_rm_modality(studies, "PT")

    # filter on description
    for fd in filter_desc:
        studies = dicom.filter_series_description(studies, "NM", fd)

    # sort series by date
    series = dicom.sort_series_by_date(studies)

    # get text for all series
    series_txt = []
    for s in series:
        t = dicom.print_series(s)
        series_txt.append({"id": s.series_idx, "text": t})

    the_cycles = Box({})
    the_cycles.cycles = Box({"cycle1": {}})
    the_cycles.cycles.cycle1.acquisitions = Box({"tp1": {}})

    choices = ["Continue to next timepoint", "Move to next cycle", "Stop"]
    decision = choices[0]
    cycle_id = "cycle1"
    tp_id = "tp1"
    print()
    while decision != choices[2]:
        cycle = the_cycles.cycles[cycle_id]
        dicom.print_current_selection(the_cycles)
        dicom.print_colored(
            f"Select CT and SPECT for cycle {cycle_id} and the timepoint {tp_id}"
        )

        # select 2 dicoms
        selected_ids = dicom.select_for_cycle(series_txt)

        # update the selected if CT and NM
        b = dicom.update_selected(cycle, series, tp_id, selected_ids)
        if not b:
            continue

        # remove selected from the list
        series_txt = [
            series for series in series_txt if series["id"] not in selected_ids
        ]

        # next decision ?
        dicom.print_current_selection(the_cycles)
        for s in series_txt:
            print(s["text"])
        dicom.print_colored("Next ?")

        # ask next
        decision = questionary.select("", choices=choices).ask()

        # next tp ?
        if decision == choices[0]:
            tp_id = dicom.next_tp_id(tp_id)
            the_cycles.cycles[cycle_id].acquisitions[tp_id] = {}

        # next cycle ?
        if decision == choices[1]:
            tp_id = "tp1"
            cycle_id = dicom.next_cycle_id(cycle_id)
            the_cycles.cycles[cycle_id] = Box()
            the_cycles.cycles[cycle_id].acquisitions = Box({"tp1": {}})

    # print
    dicom.print_current_selection(the_cycles)

    # remove unused info
    for cycle_id, cycle in the_cycles.cycles.items():
        print(f"Cycle {cycle_id}")
        for tp_id, tp in cycle.acquisitions.items():
            tp.ct_dicom = os.path.dirname(tp["ct"].filepath)
            # tp.spect_dicom = os.path.dirname(tp['spect'].filepath)
            tp.spect_dicom = tp["spect"].filepath
            del tp["ct"]
            del tp["spect"]

    # save dict
    with open(output, mode="w") as f:
        json.dump(the_cycles, f, indent=2)
    print(output)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
