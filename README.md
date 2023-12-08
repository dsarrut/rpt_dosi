



# Principle (first idea)


## (1) list of tools (+ python API)

All input image are mhd files.

- dicom_info_convert(folder) -> image + info
- resample_image(image, spacing, body_roi) -> image
- clean_crop_image(image, body_roi) -> image
- segment_ct(image) -> rois
- dose_rate(ct_image, spect_image, activity_info, options) -> dose + log + uncertainty
- dose_time_integration(dose_list, activity_info, options, rois) -> doses_txt

An issue is that we manage a large set of data and images, we need a way to store 
all the information and what each image is.

## (2) proposed workflow infrastructure

- one patient = one folder + one config file = initial
- on state file -> state of one workflow
- scripts to run/continue the workflow

      dose_rate test001_state.json test001_dose_rate_options.json


      (for one patient)
      ├── config.json                    # Initial input configuration
      ├── test001_preprocess.json        # Workflow-specific parameters (ct resampling etc)
      ├── test001_segmentation.json      # Workflow-specific parameters (roi segmentation)
      ├── test001_roi_preprocess.json    # Workflow-specific parameters (roi crop etc)
      ├── test001_dose_rate.json         # Workflow-specific parameters (dose rate calculation)
      ├── test001_dose_integration.json  # Workflow-specific parameters (dose time integration)
      ├── test001_state.json             # Workflow current state 
      │
      ├── cycle1/
      │   ├── tp1/
      │   │   ├── ct.mhd                # initial CT image
      │   │   ├── spect.mhd             # initial SPECT image
      │   │   ├── test001_rois          # <-- name of the workflow ?
      │   │   │   ├── rois.json
      │   │   │   ├── liver.mhd
      │   │   │   ├── kidney.mhd
      │   │   │   ├── body.mhd
      │   │   │   ├── ...
      │   │   ├── test001_dose 
      │   │   │   ├── 
      │   │   │   ├── resampled_ct_4mm.mhd
      │   │   │   ├── dose_rate.mhd
      │   │   │   ├── uncertainty.mhd
      │   ├── tp2/
      │   └── ...
      │
      ├── cycle2 ...
      │
      ├── test001/
      ├── test001_preprocess.json        # Workflow-specific parameters (ct resampling etc)
      ├── test001_segmentation.json      # Workflow-specific parameters (roi segmentation)
      ├── test001_roi_preprocess.json    # Workflow-specific parameters (roi crop etc)
      ├── test001_dose_rate.json         # Workflow-specific parameters (dose rate calculation)
      ├── test001_dose_integration.json  # Workflow-specific parameters (dose time integration)
      ├── cycle1/
      │   ├── tp1/
      │   │   ├── resampled_ct_4mm.mhd  # Resampled CT image
      │   │   ├── dose_rate.mhd         # Dose rate image
      │   │   ├── uncertainty.mhd       # Uncertainty image
      │   │   ├── stats.txt             # simulation stats
      │   │   ├── liver.mhd
      │   │   ├── kidney.mhd
      │   │   └── ...                
      │   │
      │   ├── tp2/