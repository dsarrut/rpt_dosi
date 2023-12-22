from .helpers import fatal
from datetime import datetime
import os
import pydicom
from collections import defaultdict
from tqdm import tqdm
from box import Box
import questionary


def dicom_read_acquisition_datetime(ds):
    try:
        # extract the date and time
        date = ds.AcquisitionDate  # DICOM date tag (0008,0022)
        time = ds.AcquisitionTime  # DICOM time tag (0008,0032)

        # convert to datetime object
        dt = dicom_date_to_str(date, time)
        return {"datetime": dt}
    except:
        fatal(f'Cannot read dicom tag Acquisition Date/Time')


def dicom_date_to_str(date, time):
    return str(datetime.strptime(date + time.split(".")[0], "%Y%m%d%H%M%S"))


def dicom_read_injection(ds):
    """
    (0054, 0016)  Radiopharmaceutical Information Sequence  1 item(s) ----
       (0018, 0031) Radiopharmaceutical                 LO: 'LU177'
       (0018, 1071) Radiopharmaceutical Volume          DS: '9.5'
       (0018, 1072) Radiopharmaceutical Start Time      TM: '100400.000'
       (0018, 1073) Radiopharmaceutical Stop Time       TM: '100400.000'
       (0018, 1074) Radionuclide Total Dose             DS: '7257.568359375'
       (0018, 1075) Radionuclide Half Life              DS: '574380.0'
       (0018, 1078) Radiopharmaceutical Start DateTime  DT: '20231012100400'
       (0018, 1079) Radiopharmaceutical Stop DateTime   DT: '20231012100400'
       (0054, 0300)  Radionuclide Code Sequence  1 item(s) ----
    """

    try:
        # Read the Radiopharmaceutical Information Sequence tag
        rad_info = ds[(0x0054, 0x0016)].value

        if len(rad_info) != 1:
            fatal(f'The dicom tag Radiopharmaceutical sequence is not equal to 1')

        item = rad_info[0]

        # Read the Radiopharmaceutical tag
        radiopharmaceutical = item[(0x0018, 0x0031)].value

        # Read the Radionuclide Total Dose tag
        total_dose = item[(0x0018, 0x1074)].value

        # Read the Radiopharmaceutical Start DateTime tag
        start_datetime = item[(0x0018, 0x1078)].value
        dt = str(datetime.strptime(start_datetime, "%Y%m%d%H%M%S"))

        return {"radionuclide": radiopharmaceutical,
                "datetime": dt,
                "activity_MBq": total_dose
                }
    except:
        s = f'Cannot read dicom tag Radiopharmaceutical'
        raise Exception(s)


def count_files(directory):
    return sum([len(files) for r, d, files in os.walk(directory)])


def list_dicom_studies_and_series(directory):
    studies = defaultdict(lambda: defaultdict(list))
    total_files = count_files(directory)

    with tqdm(total=total_files, desc="Reading DICOM files") as pbar:
        # Recursively walk through directory
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith('.dcm'):
                    filepath = os.path.join(dirpath, filename)
                    try:
                        # read dataset
                        ds = pydicom.dcmread(filepath)
                        # read uid
                        study_uid = ds.StudyInstanceUID
                        series_uid = ds.SeriesInstanceUID
                        info = store_dicom_information(ds)
                        info['filepath'] = filepath
                        studies[study_uid][series_uid].append(info)
                    except Exception as e:
                        print(f"Could not read {filepath}: {str(e)}")
                pbar.update(1)
    return studies


def store_dicom_information(ds):
    # read information
    try:
        modality = ds.Modality
    except:
        modality = "unknown modality"
    try:
        descriptions = ds.StudyDescription
        descriptions += ' ' + ds.SeriesDescription
    except:
        descriptions = "unknown description"
    try:
        datetime = dicom_date_to_str(ds.AcquisitionDate, ds.AcquisitionTime)
    except:
        datetime = "unknown datetime"
    info = {
        'modality': modality,
        'descriptions': descriptions,
        "datetime": datetime
    }
    # special case for injection ?
    if modality == "NM":
        try:
            info['injection'] = dicom_read_injection(ds)
        except:
            pass
    return info


def sort_series_by_date(studies):
    all_series = []
    study_idx = 0
    for study_uid, series in studies.items():
        for series_uid, dicom_files in series.items():
            info = Box(dicom_files[0])
            info.filenames = dicom_files
            info.study_uid = study_uid
            info.study_idx = study_idx
            info.series_uid = series_uid
            all_series.append(info)
        study_idx += 1
    sorted_series = sorted(all_series, key=lambda s: s.datetime)
    i = 0
    for s in sorted_series:
        s.series_idx = i
        i += 1
    return sorted_series


def print_series(series):
    s = ''
    if 'injection' in series:
        s = f'{series.injection.datetime} - {series.injection.activity_MBq} MBq'
    t = (f'Series {series.series_idx:<3} '
         f'Study {series.study_idx:<3} '
         f'{series.modality:<3} '
         f'{len(series.filenames):<3} files   '
         f'{series.datetime}    '
         f'{series.descriptions:<50} '
         f'{s}')
    return t


def filter_studies_include_modality(studies, mod, verbose=True):
    filtered_studies = {}
    for study_uid, series in studies.items():
        keepit = False
        for series_uid, dicom_files in series.items():
            info = dicom_files[0]
            if info['modality'] == mod:
                keepit = True
        if keepit:
            filtered_studies[study_uid] = series
    if verbose:
        print(f'Keep {len(filtered_studies)} / {len(studies)} studies'
              f' (remove studies without modality == "{mod}")')
    return filtered_studies


def filter_series_rm_modality(studies, mod, verbose=True):
    filtered_studies = {}
    nb_series = 0
    nb_filtered_series = 0
    for study_uid, series in studies.items():
        nb_series += len(series)
        filtered_series = {}
        for series_uid, dicom_files in series.items():
            info = dicom_files[0]
            if info['modality'] != mod:
                filtered_series[series_uid] = dicom_files
        filtered_studies[study_uid] = filtered_series
        nb_filtered_series += len(filtered_series)
    if verbose:
        print(f'Keep {nb_filtered_series} / {nb_series} series'
              f' (remove series when modality is "{mod}")')
    return filtered_studies


def filter_series_description(studies, modality, desc, verbose=True):
    filtered_studies = {}
    nb_series = 0
    nb_filtered_series = 0
    for study_uid, series in studies.items():
        nb_series += len(series)
        filtered_series = {}
        for series_uid, dicom_files in series.items():
            info = dicom_files[0]
            if modality != info['modality'] or desc in info['descriptions']:
                filtered_series[series_uid] = dicom_files
        filtered_studies[study_uid] = filtered_series
        nb_filtered_series += len(filtered_series)
    if verbose:
        print(f'Keep {nb_filtered_series} / {nb_series} series'
              f' (remove series when description does not contain "{desc}")')
    return filtered_studies


def next_cycle_id(current_cycle):
    # Extract the numeric part from the current cycle string
    numeric_part = "".join(filter(str.isdigit, current_cycle))

    # Increment the numeric part
    next_numeric_part = str(int(numeric_part) + 1)

    # Construct the next cycle string
    next_cycle = current_cycle.replace(numeric_part, next_numeric_part)

    return next_cycle


def next_tp_id(current_tp):
    # Extract the numeric part from the current tp string
    numeric_part = "".join(filter(str.isdigit, current_tp))

    # Increment the numeric part
    next_numeric_part = str(int(numeric_part) + 1)

    # Construct the next tp string
    next_tp = current_tp.replace(numeric_part, next_numeric_part)

    return next_tp


def select_for_cycle(cycle, series_txt):
    selected_series = []
    while len(selected_series) != 2:
        prompt_text = f"Select 2 DICOMs"
        print_colored(prompt_text, 33)
        # Use 'checkbox' prompt from questionary
        selected_series = questionary.checkbox(
            '',
            choices=[series["text"] for series in series_txt]
        ).ask()
    selected_ids = [series["id"] for series in series_txt if series["text"] in selected_series]
    return selected_ids


def highlight(question_text, color_code):
    # ANSI escape code for text color
    color_start = f"\033[38;5;{color_code}m"
    color_end = "\033[0m"  # Reset to default color

    # Combine the color code with the question text
    highlighted_question = f"{color_start}{question_text}{color_end}"

    return highlighted_question


def print_colored(text, color_code=33):
    print(f"\033[38;5;{color_code}m{text}\033[0m")


def print_current_selection(the_cycles):
    print('-' * 70)
    for cycle_id, cycle in the_cycles.cycles.items():
        print(f'Cycle {cycle_id}')
        for tp_id, tp in cycle.acquisitions.items():
            if tp:
                print(f'  Timepoint {tp_id}')
                print(f'  CT    = ', print_series(tp['ct']))
                print(f'  SPECT = ', print_series(tp['spect']))
    print('-' * 70)


def update_selected(cycle, series, tp_id, selected_ids):
    s0 = series[selected_ids[0]]
    s1 = series[selected_ids[1]]
    tp = cycle.acquisitions[tp_id]
    if s0.modality == 'CT' and s1.modality == 'NM':
        tp['ct'] = s0
        tp['spect'] = s1
    else:
        if s1.modality == 'CT' and s0.modality == 'NM':
            tp['ct'] = s1
            tp['spect'] = s0
        else:
            print('Error ! Must be one CT and one NM')
            return False
    return True
