

# (2) print series and select

    rpt_dicom_select -i dicom/P1/dicomdir.json -f -d ScC


# (1) dicom analysis 

The following command lines analyse a folder that contains DICOM files and store a json file with the list of series/studies. This json file will be used to print and select the files. 

    # for one single folder 
    rpt_dicom_browse -i dicom/P1 -o dicom/P1/dicomdir.json

    # for all folders 
    rpt_dicom_browse -i dicom -o dicomdir.json -r
    
