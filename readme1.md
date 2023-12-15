

# (4) single timepoint dose estimation with Hanscheid method


    rpt_dose_hanscheid2018 -s spect_Bq.nii.gz  --ct ct_2.5mm.nii.gz -r rois_crop/kidney_left.nii.gz "left kidney" -o a.txt -t 24 -v
    rpt_dose_hanscheid2018 -s spect_Bq.nii.gz  --ct ct_2.5mm.nii.gz  -l oar.json -o a.txt -t 24
    

# (3) spect and ct pre processing  

TODO : Partial Volume Correction

    rpt_resample_image -i ct.nii.gz -o ct_2.5mm.nii.gz --like spect.nii.gz
    rpt_spect_calibration -i spect.nii.gz -o spect_Bq.nii.gz -c 0.176906614 --concentration
    rpt_spect_calibration -i spect.nii.gz -o spect_Bqml.nii.gz -c 0.176906614


# (2) ROI segmentation

Run TotalSegmentator for all images (the option -fast can be used if too slow). Warning, a GPU is highly advised.

    cd cycle1/tp1
    TotalSegmentator -i ct.nii.gz --bs -o rois -ta body 
    TotalSegmentator -i ct.nii.gz --bs -o rois 

The output mask images are large (same size than the ct), they can be cropped with the following commands:

    rpt_roi_crop rois/* -o rois_crop


# (1) convert DICOM to mhd (manual for the moment)

Exemple of DICOM conversion, adapt the folder/filenames to your own data: 

    # CT
    gt_image_convert P1/CT/Other_/19700912/142513.288/1.250000E+00/soft_tissue_H4_C1_/*dcm -o P1_mhd/cycle1/tp1/ct.nii.gz -v
    gt_image_convert P1/CT/Other_/19700913/090804.208/1.250000E+00/soft_tissue_/*dcm -o P1_mhd/cycle1/tp2/ct.nii.gz -v
    gt_image_convert P1/CT/Other_/19700918/091617.804/1.250000E+00/soft_tissue_/*dcm -o P1_mhd/cycle1/tp3/ct.nii.gz -v

    # SPECT
    gt_image_convert P1/NM/Lu177-PSMA/19700912/142334.000/2.46/7_FFS_LU177_OSAC_Recon_Patient1_ScC_/*.dcm -o P1_mhd/cycle1/tp1/spect.nii.gz
    gt_image_convert P1/NM/Lu177-PSMA/19700913/090544.000/2.46/7_FFS_LU177_OSAC_Recon_Patient1_ScC_/*.dcm -o P1_mhd/cycle1/tp2/spect.nii.gz
    gt_image_convert P1/NM/Lu177-PSMA/19700918/091324.000/2.46/7_FFS_LU177_OSAC_Recon_Patient1_ScC_/*.dcm -o P1_mhd/cycle1/tp3/spect.nii.gz

    # visu 
    vv P1_mhd/cycle1/tp1/ct.nii.gz --fusion P1_mhd/cycle1/tp1/spect.nii.gz P1_mhd/cycle1/tp2/ct.nii.gz --fusion P1_mhd/cycle1/tp2/spect.nii.gz P1_mhd/cycle1/tp3/ct.nii.gz --fusion P1_mhd/cycle1/tp3/spect.nii.gz 

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



