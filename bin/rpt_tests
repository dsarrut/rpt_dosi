#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import pathlib
import click
import rpt_dosi
import rpt_dosi.helpers as he

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
def go():
    pathFile = pathlib.Path(__file__).parent.resolve()
    print(pathFile)
    if "tests" in os.listdir(pathFile):
        mypath = os.path.join(pathFile, "../tests/")
    else:
        mypath = os.path.join(
            pathlib.Path(rpt_dosi.__file__).resolve().parent, "../tests"
        )

    print("Look for tests in: " + mypath)

    onlyfiles = [
        f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))
    ]

    files = []
    for f in onlyfiles:
        if "test" not in f:
            continue
        files.append(f)

    files = sorted(files)
    print(f"Running {len(files)} tests")
    print(f"-" * 70)

    failure = False

    for f in files:
        start = time.time()
        print(f"Running: {f:<46}  ", end="")
        cmd = "python " + os.path.join(mypath, f"{f}")
        log = os.path.join(os.path.dirname(mypath), f"log/{f}.log")
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
                os.system("cat " + log)
        end = time.time()
        print(f"   {end - start:5.1f} s     {log:<65}")

    print(not failure)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
