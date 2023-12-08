import syd
import itk
import os
import json
import pydicom
from pydicom.tag import Tag
import sys
import shutil
import click


def mhd_file(db, image):
    mhd_file = syd.find_one(db['File'], id=image.file_mhd_id)
    return(syd.get_file_absolute_filename(db, mhd_file))

def dicom_from_mhd(db, dicom_series_id):
    dcm_folder = syd.find_one(db['DicomSeries'], id=dicom_series_id)
    return(syd.get_dicom_series_absolute_folder(db, dcm_folder))
    
def find_for_injection(db, type, patient, dataJSON):
    radionuclides = syd.find_all(db['Radionuclide'])
    radionuclide_Ga68 = syd.find_one(db['Radionuclide'], name='Ga-68')
    radionuclide_FDG = syd.find_one(db['Radionuclide'], name='F-18')
    radionuclide_Lu177 = syd.find_one(db['Radionuclide'], name='Lu-177')
    label = ""
    if type == "FDG":
        radionuclide_id=radionuclide_FDG.id
        radionuclide_name = radionuclide_FDG.name
        cycle = "PET FDG diag"
        modality = "PT"
    if type == "Ga68":
        radionuclide_id=radionuclide_Ga68.id
        radionuclide_name = radionuclide_Ga68.name
        cycle = "PET Ga68 PSMA"
        modality = "PT"
    if "cycle" in type:
        radionuclide_id=radionuclide_Lu177.id
        radionuclide_name = radionuclide_Lu177.name
        cycle = type.split("_")[0]
        cycleId = type.split("_")[0][-1]
        label = type.split("_")[1]
        modality = "NM"
    injections = syd.find(db['Injection'], patient_id=patient.id, radionuclide_id=radionuclide_id, cycle=cycle)
    injections = sorted(injections, key=lambda i: i['date'])
    iImage = 1
    if len(injections) ==0:
        print("No injection found for: " + type)
        return(dataJSON)
    for injection in injections:
        image_NM = None
        image_CT = None
        if "cycle" in type:
            images_NM = syd.find(db['Image'], injection_id=injection.id, modality=modality)
            images_CT = syd.find(db['Image'], injection_id=injection.id, modality="CT")
            for tmp in images_NM:
                if label in tmp.labels and " reconstruction " in tmp.labels:
                    image_NM = tmp
            for tmp in images_CT:
                if label in tmp.labels:
                    image_CT = tmp
        else:
            image_NM = syd.find_one(db['Image'], injection_id=injection.id, modality=modality)
            image_CT = syd.find_one(db['Image'], injection_id=injection.id, modality="CT")
        if image_NM is None or image_CT is None:
            print("No NM found for: " + type + " and " + patient.name)
            return(dataJSON)

        mhd_spect_file = dicom_from_mhd(db, image_NM.dicom_series_id)
        mhd_ct_file = dicom_from_mhd(db, image_CT.dicom_series_id)
       
        if not str(type.split("_")[0][-1]) in dataJSON["cycle"].keys():
            dataJSON["cycle"][str(type.split("_")[0][-1])] = {}
            dataJSON["cycle"][str(type.split("_")[0][-1])]["acquisition"] = []
            dataJSON["cycle"][str(type.split("_")[0][-1])]["injection"] = {
                'injection_datetime': injection.date.strftime("%d/%m/%Y, %H:%M:%S"),
                'injection_activity': injection.activity_in_mbq,
                'injection_radionuclide': radionuclide_name,
            }
        dataJSON["cycle"][str(type.split("_")[0][-1])]["acquisition"].append({
            'label': label,
            'ct': mhd_ct_file,
            'spect': mhd_spect_file,
            'roi': "",
            'date': image_NM.acquisition_date.strftime("%d/%m/%Y, %H:%M:%S"),
        })
        iImage += 1
    return(dataJSON)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)

@click.option('--db','-db', help='Input database', required=True,
              type=click.Path(dir_okay=False))
@click.option('--patient', '-p', help='Patient name', required=True, type=str)
def click_extract_patient(db, patient):
    extract_patient(db, patient)


def extract_patient(db, patient):
    db_filename = syd.get_db_filename(db)
    db = syd.open_db(db_filename)
    sydPatient = syd.find_one(db['Patient'], name=patient)
    dataJSON = {}
    dataJSON['cycle'] = {}
    dataJSON['unit'] = {
        'injection_datetime': 'dd/mm/yyyy, hh:mm:ss',
        'injection_activity': 'MBq'
    }
    dataJSON['patient'] = {
        'patient_name': sydPatient.name,
        'patient_id': sydPatient.dicom_id,
    }
    print(sydPatient.name)
    #dataJSON = find_for_injection(db, "Ga68", sydPatient, dataJSON)
    #dataJSON = find_for_injection(db, "FDG", sydPatient, dataJSON)
    dataJSON = find_for_injection(db, "cycle1_04h", sydPatient, dataJSON)
    dataJSON = find_for_injection(db, "cycle1_24h", sydPatient, dataJSON)
    dataJSON = find_for_injection(db, "cycle1_96h", sydPatient, dataJSON)
    dataJSON = find_for_injection(db, "cycle2_24h", sydPatient, dataJSON)
    dataJSON = find_for_injection(db, "cycle3_24h", sydPatient, dataJSON)
    dataJSON = find_for_injection(db, "cycle4_24h", sydPatient, dataJSON)
    dataJSON = find_for_injection(db, "cycle5_24h", sydPatient, dataJSON)
    dataJSON = find_for_injection(db, "cycle6_24h", sydPatient, dataJSON)

    with open(patient+'.json', 'w') as outfile:
            json.dump(dataJSON, outfile, indent=4)
        
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    click_extract_patient()
    
