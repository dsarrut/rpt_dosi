

# (4) single timepoint dose estimation with Madsen method


    rpt_dose_hanscheid -i spect.mhd -r rois/liver.nii.gz -c 0.176906614 -o a.txt


# (3) spect pre processing for PVC ----> FIXME <----- 

    TODO 

# Get S-values from the Opendose website

They are stored in the data folder, not need to query them.

        opendose_web_get_sources -o opendose_sources.json
        opendose_web_get_isotopes_list -o opendose_isotopes.json

        opendose_web_get_svalues -r lu177 -s "liver" -o lu177_liver.json
        opendose_web_get_svalues -r lu177 -s "spleen" -o lu177_spleen.json
        opendose_web_get_svalues -r lu177 -s "right kidney" -o lu177_right_kidney.json
        opendose_web_get_svalues -r lu177 -s "left kidney" -o lu177_left_kidney.json


# (2) ROI segmentation

Todo for all images:

    cd cycle1/tp1
    TotalSegmentator -i ct.nii.gz --bs -o rois -ta body 
    TotalSegmentator -i ct.nii.gz --bs -o rois 

The option -fast can be used if too slow. Warning, a GPU is highly advised.

# (1) convert DICOM to mhd (manual for the moment)

Exemple of DICOM conversion, adapt the folder/filenames to your own data: 

    # CT
    gt_image_convert P1/CT/Other_/19700912/142513.288/1.250000E+00/soft_tissue_H4_C1_/*dcm -o P1_mhd/cycle1/tp1/ct.nii.gz -v
    gt_image_convert P1/CT/Other_/19700913/090804.208/1.250000E+00/soft_tissue_/*dcm -o P1_mhd/cycle1/tp2/ct.nii.gz -v
    gt_image_convert P1/CT/Other_/19700918/091617.804/1.250000E+00/soft_tissue_/*dcm -o P1_mhd/cycle1/tp3/ct.nii.gz -v

    # SPECT
    gt_image_convert P1/NM/Lu177-PSMA/19700912/142334.000/2.46/7_FFS_LU177_OSAC_Recon_Patient1_ScC_/*.dcm -o P1_mhd/cycle1/tp1/spect.mhd
    gt_image_convert P1/NM/Lu177-PSMA/19700913/090544.000/2.46/7_FFS_LU177_OSAC_Recon_Patient1_ScC_/*.dcm -o P1_mhd/cycle1/tp2/spect.mhd
    gt_image_convert P1/NM/Lu177-PSMA/19700918/091324.000/2.46/7_FFS_LU177_OSAC_Recon_Patient1_ScC_/*.dcm -o P1_mhd/cycle1/tp3/spect.mhd

    # visu 
    vv P1_mhd/cycle1/tp1/ct.nii.gz --fusion P1_mhd/cycle1/tp1/spect.mhd P1_mhd/cycle1/tp2/ct.nii.gz --fusion P1_mhd/cycle1/tp2/spect.mhd P1_mhd/cycle1/tp3/ct.nii.gz --fusion P1_mhd/cycle1/tp3/spect.mhd 

We consider the folder structure as follows:
  
    patient (named P1_mhd here)
    │
    ├── cycle1/
    │   ├── tp1/                   # first timepoint
    │   │   ├── ct.nii.gz          # Original CT image
    │   │   ├── spect.nii.gz       # Original SPECT image
    │   │   └── rois/              # Segmented ROIs
    │   ├── tp2/
    │   │   ├── ct.nii.gz          # Original CT image
    │   │   ├── spect.nii.gz       # Original SPECT image
    │   │   └── rois/              # Segmented ROIs
    │   └── ...
    ├── cycle2/
    │   ├── tp1/                   # first timepoint
    │   └── ...

