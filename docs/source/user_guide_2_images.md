
## Basic Image Manipulation with Associated Metadata (sidecar JSON file)

This section delves into handling and manipulating medical imaging data within the toolkit. DICOM is the standard format for such data. For advanced processing, DICOM images should first be converted to more flexible formats like .mhd (MetaImage) or .nii (NIfTI).

**Principle.** Dosimetry involves various imaging modalities, each requiring specific handling and analysis protocols. The  primary types of images used are CT (Computed Tomography) and SPECT (Single Photon Emission Computed Tomography). Each type of imaging class is associated with distinct characteristics and units, which are crucial for accurate processing and analysis. 

**CT Images** are typically stored in units of Hounsfield Units (HU), which measure the relative density of tissue. The analysis of CT images often requires adjustments in resolution or alignment, necessitating specific tools and commands to resample or crop images based on anatomical features.

**SPECT imaging** is used to observe metabolic processes in the body by detecting the gamma rays emitted by radioactive substances introduced into the body. The units of measurement for SPECT images are critical and can include Bq (Becquerels) or Bq/ml (Becquerels per milliliter), depending on whether the focus is on total activity or concentration. It is essential to specify the correct unit when processing SPECT images to ensure that dosimetric calculations are meaningful.

**Regions of Interest (ROI)** are used for focusing analysis on specific anatomical or pathological areas within a larger image. ROIs, typically defined as mask images of contoured regions, allow for precise dosimetry calculations and targeted treatment assessments by isolating areas like organs and tumors. The toolkit facilitates ROI applications through tools for extracting and analyzing these regions, enhancing both diagnostic accuracy and treatment efficacy.

**Importance of Specifying Image Modality Type and Units.** Specifying the image type and unit is crucial in medical imaging software, as each modality and unit requires different handling techniques. For instance, software commands and functions need to know whether they are processing a CT or a SPECT image to apply appropriate filters, scaling, or conversions. The choice of units (e.g., counts, Bq, Bq/ml) impacts how data is interpreted and used in further calculations, such as dose estimation or treatment planning. Thus: the tools **require** that the user explicitly set the type (CT, SPECT) and units (HU, Bq, etc.) of the images. This can be set as commande line option or function parameter. 

**Sidecar JSON file for metadata.** We provide an additional convenient concept to handle image types, units and metadata (such as acquisition time or injected activity). Indeed, the toolkit contains tools to generate and handle sidecar JSON files that serve as companion to image files, storing detailed metadata in a flexible and interoperable format. These JSON files encapsulate data such as acquisition parameters and units of measurement, enhancing the management and compatibility of imaging data across various systems. By keeping metadata separate from the image data, sidecar JSON files maintain data integrity and facilitate easy updates, making them invaluable for both clinical practice and research where accurate and extensive metadata is critical.

Below we describe 1) how to convert from DICOM, 2) command line tools, 3) python functions and classes. 


### DICOM conversion

Conversion from DICOM to other image file format can be done with the command line `gt_image_convert` from the GateTools toolkit: 

  ```
    gt_image_convert P1/CT/*dcm -o cycle1/tp1/ct.nii.gz -v
    gt_image_convert P1/NM/32165445987321.dcm -o cycle1/tp1/spect.nii.gz
  ```

### Command line tools

- **rpt_image_set_metadata**
  Sets or updates metadata in SPECT image files, with options to add custom tags and provide detailed output. This is use primarily to set the type and the unit of the image. The metadata are stored in a file call `spect_image.mhd.json`. 

  **Usage:**
  ```
  rpt_image_set_metadata --input_image path/to/spect_image.mhd --image_type "SPECT" --unit "Bq/ml"
  rpt_image_set_metadata --input_image path/to/spect_image.mhd --tag injection_datetime "2022-02-01 12:11:00" --tag injection_activity_mbq 7504 --tag acquisition_datetime "2022-02-01 18:11:00" --tag body_weight_kg 70.4 -v
  ```

- **rpt_spect_update**
  Updates SPECT image content, allowing conversion to different units and scaling of pixel values. The metadata are still stored in a file call `updated_image.nii.gz.json`. 

  **Usage:**
  ```
  rpt_spect_update --spect path/to/spect_image.nii.gz --output path/to/updated_image.nii.gz --convert "Bq/ml" --input_unit "Bq" --scaling 1.5
  ```

- **rpt_resample_ct**
  Resamples CT images to a specified or matched spacing, essential for alignment with other imaging modalities. Because it is a CT the default pixel value is -1000 (air).

  **Usage:**
  ```
  rpt_resample_ct --input_image path/to/original_ct.nii.gz --output path/to/resampled_ct.nii.gz --like path/to/spect.mhd
  rpt_resample_ct -i path/to/original_ct.nii.gz --output path/to/resampled_ct.nii.gz --spacing 2.0 2.0 2.0
  ```

- **rpt_resample_spect**
  Resamples SPECT images to a specified or matched spacing. The default pixel value for a SPECT is 0. 

  **Usage:**
  ```
  rpt_resample_spect -i path/to/original_spect.nii.gz --output path/to/resampled_spect.nii.gz --like path/to/ct.mhd
  rpt_resample_spect --input_image path/to/original_spect.nii.gz --output path/to/resampled_spect.nii.gz --spacing 6.0 6.0 6.0
  ```

- **rpt_resample_roi**
  Resamples ROI mask images to a specified or matched spacing. The default pixel value is 0 and nearest neighbors interpolation is used.  

  **Usage:**
  ```
  rpt_resample_roi -i path/to/original_roi.nii.gz --output path/to/resampled_roi.nii.gz --like path/to/spect.mhd
  rpt_resample_roi -i path/to/original_roi.nii.gz --output path/to/resampled_roi.nii.gz --spacing 2.0 2.0 2.0
  ```

- **rpt_image_info**
  Retrieves detailed information about an image, such as dimensions, pixel intensity statistics, and metadata.

  **Usage:**
  ```
  rpt_image_info -i path/to/image.mhd
  ```

### Python functions and classes for images handling

In the toolkit, classes such as ImageBase, ImageSPECT, and others form a structured approach to handle different types of medical images. ImageBase acts as a foundational class providing common attributes and methods applicable across various image types. Derived from this base, ImageSPECT specializes in handling SPECT images, incorporating specific attributes for units like Bq or Bq/ml and methods tailored to SPECT's unique processing requirements. 

The following functions are designed to perform advanced computations and transformations on the imaging data.

- **read_spect**
  Loads SPECT imaging data into the toolkit for processing.

  **Usage example:**
  ```
  import rpt_dosi.images as rim
  spect_data = rim.read_spect('path/to/spect_file.dcm')
  ```

- **compute_total_activity()**
  Calculates the total radioactive activity within a SPECT image, an essential metric in dosimetric calculations.

  **Usage example:**
  ```
  total_activity = spect_data.compute_total_activity()
  ```

- **convert_to_suv()**
  Converts imaging data to Standardized Uptake Values (SUV), which normalize uptake data by dose and body weight.

  **Usage example:**
  ```
  suv_image = spect_data.convert_to_suv(body_weight=70)  # weight in kg
  ```

The classes ImageBase, ImageSPECT, and ImageCT offer specialized functionalities to manage and process medical images effectively:

**ImageBase** Class Functions:
- `convert_to_unit(unit)`: Converts the image's current unit to another, such as from counts to Bq/ml, ensuring data consistency across analyses.
- `set_tag(key, value)`: Attaches metadata tags to an image, such as acquisition parameters or patient data, enhancing the metadata's descriptive power.
- `write(filepath)`: Saves the image to a specified file path, preserving all modifications including converted units and newly added tags in the sidecar json file.
- `info()`: Provides a summary of the image’s metadata, including dimensions, units, and any tags set, aiding in quick assessments and integrity checks.
- Available metadata tags are : image_type unit filename description acquisition_datetime

Notes: all dates are in str format "YYYY-MM-DD HH:MM:SS" such as "2022-02-01 12:11:00".

**ImageCT** Class Specific Function:
- `compute_densities()`: Converts pixel values to densities, essential for accurately characterizing tissue properties in CT images, which is critical for precise radiation dosing.


**ImageSPECT** Class Specific Function:
- `time_from_injection_h(hours)`: Adjusts image data based on the time elapsed since the radiopharmaceutical injection, crucial for kinetic studies and dose calculations in dynamic imaging scenarios.
- Available metadata tags are : body_weight_kg injection_activity_mbq injection_datetime

```
# Assuming image_spect and image_ct are instances of ImageSPECT and ImageCT respectively

# Convert units for a SPECT image
image_spect.convert_to_unit("Bq/ml")

# Set a new tag for patient ID
image_spect.set_tag("injection_datetime", "2022-02-01 12:11:00")

# Write the modified image to disk with the associated JSON sidecar.
image_spect.write("path/to/modified_image.mhd")

# Retrieve and print image information
print(image_spect.info())

# Compute tissue densities for a CT image
densitiy_image = image_ct.compute_densities()

# Adjust SPECT image data for time elapsed since injection
image_spect.time_from_injection_h(2)

```