

# (2) print series, select and convert dicoms

    # select the dicoms (one by one, manually)
    rpt_dicom_select -i dicom/P1/dicomdir.json -f -d ScC -o dicom/P1/selected.json
    
    # convert to nii and create the db ; add -r option to run the conversion
    rpt_dicom_db -i dicom/P1/selected.json -o P1


# (1) dicom analysis 

The following command lines analyse a folder that contains DICOM files and store a json file with the list of series/studies. This json file will be used to print and select the files. 

    # for one single folder 
    rpt_dicom_browse -i dicom/P1 -o dicom/P1/dicomdir.json

    # for all folders 
    rpt_dicom_browse -i dicom -o dicomdir.json -r
    
