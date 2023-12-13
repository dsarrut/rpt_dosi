import json
from box import Box
import inspect
import colored
import Levenshtein


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
    required_keys = ["cycles"]
    check_required_keys(param, required_keys)
    return param


def check_required_keys(param, required_keys):
    for k in required_keys:
        if k not in param:
            fatal(f"Cannot find the required key '{k} in the param {param}")


def find_closest_match(input_string, string_list):
    # Initialize with a large distance
    min_distance = float("inf")
    closest_match = None

    for candidate in string_list:
        distance = Levenshtein.distance(input_string.lower(), candidate.lower())
        # print(f"Distance between {input_string} and {candidate} is {distance}")
        if distance < min_distance:
            min_distance = distance
            closest_match = candidate

    return closest_match
