import json
import os
from box import Box
import inspect
import colored
import Levenshtein
import rpt_dosi
from pathlib import Path
import sys
import math

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


def get_roi_list(filename):
    # open the file
    with open(filename, "r") as f:
        data = json.load(f)
    l = []
    for item in data:
        l.append((item["roi_filename"], item["roi_name"]))
    return l


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

def create_oar_file(folder):
    if not os.path.isfile(os.path.join(folder, "data", "oar_realpath.json")):
        oars = get_roi_list(os.path.join(folder, "data", "oar.json"))
        output_oars = []
        for roi_file, roi_name in oars:
            roi_file = os.path.join(folder, roi_file)
            output_oars.append({
                "roi_filename": roi_file,
                "roi_name": roi_name,
            })
        with open(os.path.join(folder, "data", "oar_realpath.json"), 'w') as filehandle:
            json_object = json.dumps(output_oars, indent=4)
            filehandle.write(json_object)


def get_tests_folder():
    current_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    folder = current_dir / ".." / "tests"
    # Create oar.json with realpath
    create_oar_file(folder)
    return folder


def get_data_folder():
    current_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    folder = current_dir / "data"
    return folder


def get_tests_data_folder(sub_folder=None):
    folder = os.path.join(get_tests_folder(), "data")
    if sub_folder is not None:
        folder = os.path.join(folder, sub_folder)
        os.makedirs(folder, exist_ok=True)
    return Path(folder)


def get_tests_output_folder(sub_folder=None):
    folder = os.path.join(get_tests_folder(), "output")
    if sub_folder is not None:
        folder = os.path.join(folder, sub_folder)
        os.makedirs(folder, exist_ok=True)
    return Path(folder)


def get_tests_folders(test_name):
    data_folder = get_tests_data_folder()
    ref_folder = get_tests_data_folder(test_name)
    output_folder = get_tests_output_folder(test_name)
    return data_folder, ref_folder, output_folder


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
        current_depth = root[len(folder_path) + len(os.path.sep) :].count(os.path.sep)
        if current_depth == depth:
            for dir in dirs:
                subfolders.append(os.path.join(root, dir))
        if current_depth >= depth:
            break
    return subfolders


def escape_special_characters(filename):
    # Add more characters to escape as needed
    special_characters = ["?", "#", "&", "$", "|", ";", "<", ">", "(", ")"]
    for char in special_characters:
        filename = filename.replace(char, "\\" + char)
    return filename


def are_dicts_equal(dict1, dict2, float_tolerance=1e-9):
    for key, value1 in dict1.items():
        if key not in dict2:
            return False

        value2 = dict2[key]

        if isinstance(value1, dict) and isinstance(value2, dict):
            if not are_dicts_equal(value1, value2, float_tolerance):
                return False
        elif isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            if not math.isclose(value1, value2, abs_tol=float_tolerance):
                return False
        else:
            return False

    for key in dict2.keys():
        if key not in dict1:
            return False

    return True
