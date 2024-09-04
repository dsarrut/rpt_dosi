from datetime import datetime
import os
import pydicom
from collections import defaultdict
from tqdm import tqdm
from box import Box
import questionary
from rpt_dosi.utils import fatal
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import json
import gatetools as gt
import itk
import subprocess


def dicom_read_acquisition_datetime(ds):
    try:
        # extract the date and time
        date = ds.AcquisitionDate  # DICOM date tag (0008,0022)
        time = ds.AcquisitionTime  # DICOM time tag (0008,0032)

        # convert to datetime object
        dt = dicom_date_to_str(date, time)
        return dt
    except:
        fatal(f"Cannot read dicom tag Acquisition Date/Time")


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
            fatal(f"The dicom tag Radiopharmaceutical sequence is not equal to 1")

        item = rad_info[0]

        # Read the Radiopharmaceutical tag
        radiopharmaceutical = item[(0x0018, 0x0031)].value

        # Read the Radionuclide Total Dose tag
        total_dose = item[(0x0018, 0x1074)].value

        # Read the Radiopharmaceutical Start DateTime tag
        start_datetime = item[(0x0018, 0x1078)].value
        dt = str(datetime.strptime(start_datetime, "%Y%m%d%H%M%S"))

        return {
            "radionuclide": radiopharmaceutical,
            "datetime": dt,
            "activity_MBq": total_dose,
        }
    except:
        s = f"Cannot read dicom tag Radiopharmaceutical"
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
                if filename.endswith(".dcm"):
                    filepath = os.path.join(dirpath, filename)
                    try:
                        # read dataset
                        ds = pydicom.dcmread(filepath)
                        # read uid
                        study_uid = ds.StudyInstanceUID
                        series_uid = ds.SeriesInstanceUID
                        info = store_dicom_information(ds)
                        info["filepath"] = filepath
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
        descriptions += " " + ds.SeriesDescription
    except:
        descriptions = "unknown description"
    try:
        datetime = dicom_date_to_str(ds.AcquisitionDate, ds.AcquisitionTime)
    except:
        datetime = "unknown datetime"
    try:
        content_datetime = dicom_date_to_str(ds.ContentDate, ds.ContentTime)
    except:
        content_datetime = "unknown datetime"
    try:
        ic_datetime = dicom_date_to_str(ds.InstanceCreationDate, ds.InstanceCreationTime)
    except:
        ic_datetime = "unknown datetime"

    info = {"modality": modality,
            "descriptions": descriptions,
            "acquisition_datetime": datetime,
            "content_datetime": content_datetime,
            "instance_creation_datetime": ic_datetime}
    # special case for injection ?
    if modality == "NM":
        try:
            info["injection"] = dicom_read_injection(ds)
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
    sorted_series = sorted(all_series, key=lambda s: s.acquisition_datetime)
    i = 0
    for s in sorted_series:
        s.series_idx = i
        i += 1
    return sorted_series


def print_series(series):
    s = ""
    if "injection" in series:
        s = f"{series.injection.datetime} - {series.injection.activity_MBq} MBq"
    dt = ''
    # if series.content_datetime != series.acquisition_datetime:
    #    dt += f'content={series.content_datetime}'
    # if series.instance_creation_datetime != series.acquisition_datetime:
    #    dt += f'    inst={series.instance_creation_datetime}'
    t = (
        f"Series {series.series_idx:<3} "
        f"Study {series.study_idx:<3} "
        f"{series.modality:<3} "
        f"{len(series.filenames):<3} files   "
        f"{series.acquisition_datetime}    "
        f"{series.instance_creation_datetime}    "
        f"{series.descriptions:<50} "
        f"{s}"
    )
    return t


def filter_studies_include_modality(studies, mod, verbose=True):
    filtered_studies = {}
    for study_uid, series in studies.items():
        keepit = False
        for series_uid, dicom_files in series.items():
            info = dicom_files[0]
            if info["modality"] == mod:
                keepit = True
        if keepit:
            filtered_studies[study_uid] = series
    if verbose:
        print(
            f"Keep {len(filtered_studies)} / {len(studies)} studies"
            f' (remove studies without modality == "{mod}")'
        )
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
            if info["modality"] != mod:
                filtered_series[series_uid] = dicom_files
        filtered_studies[study_uid] = filtered_series
        nb_filtered_series += len(filtered_series)
    if verbose:
        print(
            f"Keep {nb_filtered_series} / {nb_series} series"
            f' (remove series when modality is "{mod}")'
        )
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
            if modality != info["modality"] or desc in info["descriptions"]:
                filtered_series[series_uid] = dicom_files
        filtered_studies[study_uid] = filtered_series
        nb_filtered_series += len(filtered_series)
    if verbose:
        print(
            f"Keep {nb_filtered_series} / {nb_series} series"
            f' (remove series when description does not contain "{desc}")'
        )
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


def select_for_cycle(series_txt):
    selected_series = []
    while len(selected_series) != 2:
        prompt_text = f"Select 2 DICOMs"
        print_colored(prompt_text, 33)
        # Use 'checkbox' prompt from questionary
        selected_series = questionary.checkbox(
            "", choices=[series["text"] for series in series_txt]
        ).ask()
    selected_ids = [
        series["id"] for series in series_txt if series["text"] in selected_series
    ]
    return selected_ids


def print_colored(text, color_code=33):
    print(f"\033[38;5;{color_code}m{text}\033[0m")


def print_current_selection(the_cycles):
    print("-" * 70)
    for cycle_id, cycle in the_cycles.cycles.items():
        print(f"Cycle {cycle_id}")
        for tp_id, tp in cycle.acquisitions.items():
            if tp:
                print(f"  Timepoint {tp_id}")
                print(f"  CT    = ", print_series(tp["ct"]))
                print(f"  SPECT = ", print_series(tp["spect"]))
    print("-" * 70)


def update_selected(cycle, series, tp_id, selected_ids):
    s0 = series[selected_ids[0]]
    s1 = series[selected_ids[1]]
    tp = cycle.acquisitions[tp_id]
    if s0.modality == "CT" and s1.modality == "NM":
        tp["ct"] = s0
        tp["spect"] = s1
    else:
        if s1.modality == "CT" and s0.modality == "NM":
            tp["ct"] = s1
            tp["spect"] = s0
        else:
            print("Error ! Must be one CT and one NM")
            return False
    return True


def convert_ct_dicom_to_image(dicom_folder, output_filename):
    print(dicom_folder, output_filename)
    series = gt.separate_series(dicom_folder)
    series = gt.separate_sequenceName_series(series)
    print(series)
    if len(series) >= 1:
        fatal(f'Cannot read DICOM folder, it contains several series')
    files = series[0]
    print(files)
    itk_image = gt.read_dicom(files)


class DicomSelectionGUI(tk.Tk):
    def __init__(self, data_dict, json_filename):
        super().__init__()
        self.entry_widget = None
        self.data_dict = data_dict
        self.json_filename = json_filename
        self.tree = None
        self.columns_keys = None
        self.title(f"Select dicom {json_filename}")
        self.geometry("1200x600")

        if os.path.exists(self.json_filename):
            self.load_from_json(json_filename)
        else:
            self.data_dict = data_dict

        # Create left frame
        self.left_frame = tk.Frame(self)
        self.left_frame.pack(side="left", fill="both", expand=True)

        # Add 'Save to JSON' button above the treeview on the left
        self.save_button = tk.Button(self.left_frame, text="Save to JSON", command=self.save_to_json)
        self.save_button.pack(pady=10, padx=10, anchor=tk.NW)  # Place it at the top with some margins

        # Main frame for layout
        #self.main_frame = tk.Frame(self)
        #self.main_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # Left frame for data treeview
        #self.left_frame = tk.Frame(self.main_frame)
        #self.left_frame.pack(side=tk.LEFT, padx=(0, 20), fill=tk.BOTH, expand=True)

        # initial data
        self.make_data_tree(self.data_dict)

        # Save button
        #self.save_button = tk.Button(self.main_frame, text="Save to JSON", command=self.save_to_json)
        #self.save_button.pack(pady=20)

        self.right_frame = tk.Frame(self)
        self.right_frame.pack(side="left", fill="both", expand=True)

    def make_data_tree(self, data_dict):
        self.columns_keys = ('series_idx',
                             'vv',
                             'cycle_id',
                             'tp_id',
                             'name',
                             'modality',
                             'descriptions',
                             'acquisition_datetime',
                             'instance_creation_datetime',
                             'filepath')
        for item in data_dict:
            item['vv'] = 'vv'
        font = tkFont.Font()

        self.tree = ttk.Treeview(self.left_frame, columns=self.columns_keys, show="headings")
        for key in self.columns_keys:
            self.tree.heading(key, text=key)
            self.tree.column(key, stretch=False)
            max_width = max([font.measure(str(item[key])) for item in data_dict] + [font.measure(key)])
            if key == 'name':
                max_width = max_width * 2
            if key == 'vv':
                max_width = max_width * 2
            self.tree.column(key, width=max_width)

        # Insert data into the treeview
        for item in data_dict:
            values = [item[key] for key in self.columns_keys]
            item_id = item['series_idx']
            self.tree.insert("", "end", iid=item_id, values=values + ['Click Here'])

        # click
        self.tree.bind('<ButtonRelease-1>', self.run_vv)
        self.tree.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)
        self.tree.bind('<Double-1>', self.on_double_click)

    def on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            row = self.tree.identify_row(event.y)
            column_name = self.tree.heading(column)["text"]

            if column_name in ['cycle_id', 'tp_id', 'name']:
                self.edit_cell(row, column, column_name)

    def run_vv(self, event):
        # Get item id of the selected row
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        # Get column index of the clicked cell
        col = int(self.tree.identify_column(event.x)[1:]) - 1
        series_data = next((item for item in self.data_dict if item['series_idx'] == int(item_id)), None)

        # Check whether the hyperlink column was clicked
        if self.columns_keys[col] == 'vv':
            print(f"vv {series_data['filepath']}")
            # Launch the 'vv' command line for item
            subprocess.call(['vv', series_data['filepath']])

    def edit_cell(self, row, column, column_name):
        # Get the bounding box of the cell
        x, y, width, height = self.tree.bbox(row, column)
        value = self.tree.set(row, column_name)

        # Create an entry widget for editing
        self.entry_widget = tk.Entry(self.tree)
        self.entry_widget.place(x=x, y=y, width=width, height=height)
        self.entry_widget.insert(0, value)
        self.entry_widget.focus()

        # Bind the entry widget to handle the editing
        self.entry_widget.bind("<Return>", lambda event: self.save_edit(row, column_name))
        self.entry_widget.bind("<FocusOut>", lambda event: self.save_edit(row, column_name))

    def save_edit(self, row, column_name):
        new_value = self.entry_widget.get()
        self.tree.set(row, column_name, new_value)
        self.update_data_dict(row, column_name, new_value)
        self.entry_widget.destroy()
        self.entry_widget = None

    def update_data_dict(self, item_id, column_name, new_value):
        for item in self.data_dict:
            if item['series_idx'] == int(item_id):
                if new_value != "":
                    self.auto_update_item_name(item_id, item)
                item[column_name] = new_value
                break

    def auto_update_item_name(self, row, item):
        modality = item['modality'].lower()
        if modality == 'pt':
            modality = "pet"
        if modality == 'nm':
            modality = "spect"
        name = f'dicom_{modality}'
        self.tree.set(row, 'name', name)
        item['name'] = name

    def save_to_json(self):
        filtered_data = [{key: item.get(key, '')
                          for key in self.columns_keys}
                         for item in self.data_dict]
        with open(self.json_filename, 'w') as json_file:
            json.dump(filtered_data, json_file, indent=4)
        print(f"Data saved to {self.json_filename}")

    def load_from_json(self, json_filename):
        with open(json_filename, 'r') as json_file:
            self.data_dict = json.load(json_file)


def get_files_in_folder(directory):
    files = []
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            files.append(filepath)
    return files


def convert_dicom_to_image(input_dicom_files, dest_file, pixel_type='float'):
    series = gt.separate_series(input_dicom_files)
    # series = gt.separate_sequenceName_series(series)

    input_images = []
    for serie in series.keys():
        if len(series[serie]) > 1:
            input_images.append(gt.read_dicom(series[serie]))
        elif (len(series[serie]) == 1 and
              (series[serie][0].endswith(".dcm") or series[serie][0].endswith(".IMA"))):
            input_images.append(gt.read_3d_dicom(series[serie], flip=True))
        else:
            fatal(f'Cannot read DICOM from {input_dicom_files[0]}')
    if len(input_images) > 1:
        fatal(f'Several DICOM images found {input_dicom_files[0]}')

    outputImage = gt.image_convert(input_images[0], pixeltype=pixel_type)
    itk.imwrite(outputImage, dest_file)
