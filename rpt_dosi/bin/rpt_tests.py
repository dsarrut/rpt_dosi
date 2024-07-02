#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import click
import rpt_dosi.utils as he
from pathlib import Path

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
def go():
    tests_folder = Path(he.get_tests_folder())
    print("Look for tests in: ", tests_folder)
    log_folder = tests_folder / "log"

    tests_files = [
        f
        for f in os.listdir(tests_folder)
        if os.path.isfile(os.path.join(tests_folder, f))
    ]

    files = []
    for f in tests_files:
        if "test" not in f:
            continue
        if "wip" in f:
            continue
        files.append(f)

    files = sorted(files)
    print(f"Running {len(files)} tests")
    print(f"-" * 70)

    failure = False

    for f in files:
        start = time.time()
        print(f"Running: {f:<46}  ", end="")
        cmd = "python " + str(tests_folder / f)
        log = str(log_folder / f"{f}.log")
        r = os.system(f"{cmd} > {log} 2>&1")
        # subprocess.run(cmd, stdout=f, shell=True, check=True)
        if r == 0:
            print(he.colored.stylize(" OK", he.color_ok), end="")
        else:
            if r == 2:
                # this is probably a Ctrl+C, so we stop
                he.fatal("Stopped by user")
            else:
                print(he.colored.stylize(" FAILED !", he.color_error), end="")
                failure = True
                with open(log, 'r') as f:
                    print(f.read())
        end = time.time()
        print(f"   {end - start:5.1f} s     {log:<65}")

    print(not failure)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
