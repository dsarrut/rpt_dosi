import json
import os
from box import Box
import inspect
import colored
import Levenshtein
from pathlib import Path
import sys
import math
import collections.abc
from dateutil import parser

try:
    color_error = colored.fg("red") + colored.attr("bold")
    color_warning = colored.fg("orange_1")
    color_ok = colored.fg("green")
except AttributeError:
    # new syntax in colored>=1.5
    color_error = colored.fore("red") + colored.style("bold")
    color_warning = colored.fore("orange_1")
    color_ok = colored.fore("green")


class RptError(Exception):
    pass


def fatal(s, stop_and_exit=False):
    caller = inspect.getframeinfo(inspect.stack()[1][0])
    ss = f"(in {caller.filename} line {caller.lineno})"
    ss = colored.stylize(ss, color_error)
    print(ss)
    s = colored.stylize(s, color_error)
    print(s)
    if stop_and_exit:
        exit()
    # the following trick avoid to print the traceback when fail
    try:
        raise RptError(s)
    except RptError:
        exit()


def warning(s):
    s = colored.stylize(s, color_warning)
    print(s)


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


def get_tests_folder():
    current_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    folder = current_dir / ".." / "tests"
    return folder


def get_data_folder():
    current_dir = Path(os.path.dirname(os.path.realpath(__file__)))
    folder = current_dir / "data"
    return folder


def get_tests_data_folder(sub_folder=None):
    folder = get_tests_folder() / "data"
    if sub_folder is not None:
        folder = folder / sub_folder
        os.makedirs(folder, exist_ok=True)
    return Path(folder)


def get_tests_output_folder(sub_folder=None):
    folder = get_tests_folder() / "output"
    if sub_folder is not None:
        folder = folder / sub_folder
        os.makedirs(folder, exist_ok=True)
    return Path(folder)


def get_tests_folders(test_name):
    data_folder = get_tests_data_folder()
    ref_folder = get_tests_data_folder(test_name)
    output_folder = get_tests_output_folder(test_name)
    return data_folder, ref_folder, output_folder


def print_tests(is_ok, s):
    if not is_ok:
        s = colored.stylize(f'TEST ERROR : {s}', color_error)
    else:
        s = colored.stylize(s, color_ok)
    print(s)
    return is_ok


def test_ok(is_ok=False):
    if is_ok:
        s = "Great, all tests are ok."
        s = "\n" + colored.stylize(s, color_ok)
        print(s)
        # sys.exit(0)
    else:
        s = "Error during the tests !"
        s = "\n" + colored.stylize(s, color_error)
        print(s)
        sys.exit(-1)


class SimpleTest:
    _test_num = 1
    _global_ok_flag = True
    _first_failing_test = None

    def __init__(self, msg):
        print()
        print('-' * 80)
        warning(f'[{self._test_num}] {msg}')

    @staticmethod
    def stop_current_test(ok, msg):
        print_tests(ok, f'{msg}: {ok}')
        SimpleTest._global_ok_flag = SimpleTest._global_ok_flag and ok
        if not ok and SimpleTest._first_failing_test is None:
            SimpleTest._first_failing_test = SimpleTest._test_num
        SimpleTest._test_num += 1

    @staticmethod
    def get_final_ok():
        return SimpleTest._global_ok_flag

    @staticmethod
    def get_number_of_tests():
        return SimpleTest._test_num - 1

    @staticmethod
    def get_first_failing_test():
        return SimpleTest._first_failing_test


def start_test(msg):
    return SimpleTest(msg)


def stop_test(ok, msg, ):
    SimpleTest.stop_current_test(ok, msg)


def end_tests():
    ok = SimpleTest.get_final_ok()
    print()
    if ok:
        s = f"Great, all {SimpleTest.get_number_of_tests()} tests are ok."
        print(colored.stylize(s, color_ok))
        # sys.exit(0)
    else:
        s = ("Error during the tests !\n"
             f"First fail test is {SimpleTest.get_first_failing_test()}")
        print(colored.stylize(s, color_error))
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
    special_characters = ["?", "#", "&", "$", "|", ";", "<", ">", "(", ")"]
    for char in special_characters:
        filename = filename.replace(char, "\\" + char)
    return filename


def compare_dict(dict1, dict2):
    msg = ''
    ok = True
    for key, v in dict1.items():
        if key not in dict2:
            msg = f'{key}: not in dict2\n'
            ok = False
        else:
            if dict2[key] != v:
                msg = f'{key}= {v} vs {dict2[key]}\n'
                ok = False
    for key, v in dict2.items():
        if key not in dict1:
            msg = f'{key}: not in dict1\n'
            ok = False
    # remove final line break
    msg = msg.rstrip('\n')
    return ok, msg


def are_dicts_float_equal(dict1, dict2, float_tolerance=1e-9):
    for key, value1 in dict1.items():
        if key not in dict2:
            s = key + " is not in dict2"
            print(colored.stylize(s, color_error))
            return False

        value2 = dict2[key]

        if isinstance(value1, dict) and isinstance(value2, dict):
            if not are_dicts_float_equal(value1, value2, float_tolerance):
                return False

        elif isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            if not math.isclose(value1, value2, abs_tol=float_tolerance):
                s = "The number values are not equals: " + str(value1) + " vs. " + str(value2) + " tol= " + str(
                    float_tolerance)
                print(colored.stylize(s, color_error))
                return False

        elif isinstance(value1, str) and isinstance(value2, str):
            # special case on windows for path
            if "\\" in value1:
                value1 = value1.replace("\\", "/")
            if not value1 == value2:
                s = "The strings values are not equals: " + str(value1) + " vs. " + str(value2)
                print(colored.stylize(s, color_error))
                return False

        elif isinstance(value1, collections.abc.Sequence) and isinstance(value2, collections.abc.Sequence):
            nbElement = len(value1)
            if not nbElement == len(value2):
                print("The array lengths are not equals: " + str(value1) + " vs. " + str(value2))
                return False
            for i in range(0, nbElement):
                if not are_dicts_float_equal(value1[i], value2[i], float_tolerance):
                    return False

        elif isinstance(value1, type(None)) and not isinstance(value2, type(None)):
            s = f"ERROR: '{key}' value1 is None but  value2 = {value2}"
            print(colored.stylize(s, color_error))
            return False

        elif not isinstance(value1, type(None)) and isinstance(value2, type(None)):
            s = f"ERROR: '{key}' value2 is None but value1 = {value1}"
            print(colored.stylize(s, color_error))
            return False

        elif not isinstance(value1, type(None)) and not isinstance(value2, type(None)):
            s = (f"ERROR: the values are not int/float/dict/str, "
                 f"cannot be compared key '{key}' : {str(value1)} vs. {str(value2)}, "
                 f"type1 is {type(value1)} and type2 is {type(value2)}")
            print(colored.stylize(s, color_error))
            return False

    for key in dict2.keys():
        if key not in dict1:
            s = key + " is not in dict1"
            print(colored.stylize(s, color_error))
            return False

    return True


def run_cmd(cmd, folder=None):
    pwd_initial = os.getcwd()
    if folder is not None:
        os.chdir(folder)
    pwd = os.getcwd()
    print(cmd)
    r = os.system(cmd)
    os.chdir(pwd_initial)
    return r == 0


def indent(input_str, indentation='\t'):
    lines = input_str.splitlines()
    indented_lines = [indentation + line for line in lines]
    return '\n'.join(indented_lines)


def get_basename_and_extension(filename):
    """Return the basename and extension of a filename even if .nii.gz is used."""
    base = filename
    extensions = []
    while os.path.splitext(base)[1]:
        base, ext = os.path.splitext(base)
        extensions.append(ext)
    extensions.reverse()
    return os.path.basename(base), ''.join(extensions)


def convert_datetime(value):
    try:
        dt = parser.parse(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        fatal(f"Invalid date format '{value}', we expect '%Y-%m-%d %H:%M:%S'")

