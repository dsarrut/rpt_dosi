from .helpers import fatal
from datetime import datetime
import os
import pydicom
from collections import defaultdict
from tqdm import tqdm
from box import Box


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


def print_serie(series):
    s = ''
    if 'injection' in series:
        s = f'{series.injection.datetime} - {series.injection.activity_MBq} MBq'
    print(f'Series {series.series_idx:<3} '
          f'Study {series.study_idx:<3} '
          f'{series.modality:<3} '
          f'{len(series.filepath):<3} files   '
          f'{series.datetime}    '
          f'{series.descriptions:<50} '
          f'{s}')


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
        print(f'Filtered {len(filtered_studies)} / {len(studies)} studies'
              f' (modality without "{mod}")')
    return filtered_studies


def filter_series_rm_modality(studies, mod, verbose=True):
    filtered_studies = {}
    for study_uid, series in studies.items():
        filtered_series = {}
        for series_uid, dicom_files in series.items():
            info = dicom_files[0]
            if info['modality'] != mod:
                filtered_series[series_uid] = dicom_files
        filtered_studies[study_uid] = filtered_series
    if verbose:
        print(f'Filtered {len(filtered_studies)} / {len(studies)} studies'
              f' (modality is not "{mod}")')
    return filtered_studies
