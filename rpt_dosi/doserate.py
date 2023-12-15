import json
from box import Box
import inspect
import colored


try:
    color_error = colored.fg("red") + colored.attr("bold")
    color_warning = colored.fg("orange_1")
    color_ok = colored.fg("green")
except AttributeError:
    # new syntax in colored>=1.5
    color_error = colored.fore("red") + colored.style("bold")
    color_warning = colored.fore("orange_1")
    color_ok = colored.fore("green")


def fatal(s):
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    ss = f"(in {caller.filename} line {caller.lineno})"
    ss = colored.stylize(ss, color_error)
    print(ss)
    s = colored.stylize(s, color_error)
    print(s)
    raise Exception(s)

def read_and_check_input_infos(json_file):
    # read
    print(json_file)
    f = open(json_file).read()
    param = Box(json.loads(f))

    # check
    required_keys = ['cycles']
    check_required_keys(param, required_keys)


def check_required_keys(param, required_keys):
    for k in required_keys:
        if k not in param:
            fatal(f"Cannot find the required key '{k} in the param {param}")


def read_dose_rate_options(json_file):
    print(json_file)
    if json_file is None:
        options = init_dose_rate_options()
    else:
        f = open(json_file).read()
        options = Box(json.loads(f))
    check_dose_rate_options(options)
    return options

def check_dose_rate_options(options):
    ref = init_dose_rate_options()
    check_required_keys(options, ref.keys())


def init_dose_rate_options():
    options = Box()
    options.number_of_threads = 1
    options.density_tolerance_gcm3 = 0.1
    return options