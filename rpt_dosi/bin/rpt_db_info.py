#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import rpt_dosi.db as rdb
import rpt_dosi.helpers as rhe

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument('db_file', type=click.Path(exists=True), required=True)
@click.option('--verbose', "-v", is_flag=True, help='Print detailed info')
@click.option('--large_verbose', "-vv", '--vv', is_flag=True, help='Print more detailed info')
def go(db_file, verbose, large_verbose):
    # open db
    db = rdb.PatientTreatment(db_file)

    # print
    print(db.info())

    # detailed info
    if verbose:
        for cycle in db.cycles.values():
            print(rhe.indent(str(cycle)))
            for tp in cycle.timepoints.values():
                print(rhe.indent(str(tp), '\t\t'))

    # more detailed info
    if large_verbose:
        for cycle in db.cycles.values():
            print(rhe.indent(cycle.info()))
            for tp in cycle.timepoints.values():
                print(rhe.indent(tp.info(), '\t\t'))


if __name__ == "__main__":
    go()
