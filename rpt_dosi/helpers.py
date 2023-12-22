import json
import os
from box import Box
import inspect
import colored
import Levenshtein
import pkg_resources
from path import Path
import sys

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

    return closest_match, min_distance


def get_tests_data_folder(sub_folder=None):
    folder = pkg_resources.resource_filename("rpt_dosi", f"../tests/data")
    if sub_folder is not None:
        folder = os.path.join(folder, sub_folder)
        os.makedirs(folder, exist_ok=True)
    return Path(folder)


def print_tests(is_ok, s):
    if not is_ok:
        s = colored.stylize(s, color_error)
    else:
        s = colored.stylize(s, color_ok)
    print(s)


def test_ok(is_ok=False):
    if is_ok:
        s = "Great, tests are ok."
        s = "\n" + colored.stylize(s, color_ok)
        print(s)
        # sys.exit(0)
    else:
        s = "Error during the tests !"
        s = "\n" + colored.stylize(s, color_error)
        print(s)
        sys.exit(-1)


def get_subfolders(folder_path, depth=1):
    subfolders = []
    for root, dirs, files in os.walk(folder_path):
        current_depth = root[len(folder_path) + len(os.path.sep):].count(os.path.sep)
        if current_depth == depth:
            for dir in dirs:
                subfolders.append(os.path.join(root, dir))
        if current_depth >= depth:
            break
    return subfolders


def escape_special_characters(filename):
    # Add more characters to escape as needed
    special_characters = ['?', '#', '&', '$', '|', ';', '<', '>', '(', ')']
    for char in special_characters:
        filename = filename.replace(char, '\\' + char)
    return filename
