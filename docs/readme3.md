

# (4) perform the SPECT calibration and add the ROIs in the db

    rpt_db_spect_calibration --db p1/db.json -c 0.176906614
    rpt_db_add_rois --db p1/db.json -l oar.json -n p1
    rpt_db_rois_activity --db p1/db.json
    rpt_db_info --db BC4/db.json


# (3) update the dates (injection and spect) in the json

Injection date must be set manually in the json for every "cycle":

    "injection": {
      "radionuclide": "LU177",
      "datetime": "2021-09-22 12:00:00",
      "activity_MBq": 6155
    }

Image acquisitions dates can be extracted from dicom: 

    rpt_db_set_spect_datetime_from_dicom.py --db p1/db.json

Information about the db can be printed: 

    rpt_db_info --db 11/db.json


# (2) print series, select and convert dicom files

    # select the dicoms (one by one, manually)
    rpt_dicom_select -i dicom/p1/dicomdir.json -f -d ScC -o dicom/p1/selected.json

    # convert to nii and create the db ; add -r option to run the conversion
    rpt_dicom_db -i dicom/p1/selected.json -o p1

    # segmentator
    ./rpt_segment p1



# (1) dicom analysis

The following command lines analyse a folder that contains DICOM files and store a json file with the list of series/studies. This json file will be used to print and select the files.

    # for one single folder
    rpt_dicom_browse -i dicom/p1 -o dicom/p1/dicomdir.json

    # for all folders
    rpt_dicom_browse -i dicom -o dicomdir.json -r
