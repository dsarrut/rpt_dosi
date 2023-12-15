from .helpers import fatal
from datetime import datetime


def dicom_read_acquisition_datetime(ds):
    try:
        # extract the date and time
        date = ds.AcquisitionDate  # DICOM date tag (0008,0022)
        time = ds.AcquisitionTime  # DICOM time tag (0008,0032)

        # convert to datetime object
        dt = datetime.strptime(date + time.split(".")[0], "%Y%m%d%H%M%S")
        return {"datetime": str(dt)}
    except:
        fatal(f'Cannot read dicom tag Acquisition Date/Time')


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
        dt = datetime.strptime(start_datetime, "%Y%m%d%H%M%S")

        return {"radionuclide": radiopharmaceutical,
                "datetime": str(dt),
                "activity_MBq": total_dose
                }
    except:
        fatal(f'Cannot read dicom tag Radiopharmaceutical')
