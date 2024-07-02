
## Basic Image Manipulation with Associated Metadata (sidecar JSON file)

**Metadata** This section delves into handling and manipulating medical imaging data within the toolkit. We propose functions and classes to manage images together with the associated **metadata** that are needed for dose computation (such as injected activity of acquisition time) and image units: Bq, SUV, etc. 

**Image file format** DICOM is the standard format. However, for advanced processing, DICOM images are sometimes converted to more flexible formats like .mhd (MetaImage) or .nii (NIfTI).


### MetaImage API

Here are the basics CRUD operations (Create Read Update Delete) for the MetaImage. 

First, how to CREATE a metadata image: 

```python
import rpt_dosi.images as rim
image = rim.new_metaimage('SPECT', "path/spect.nii.gz", unit='Bq')
image.write_metadata()
```

This script will create a new metaimage with SPECT as image type and 'Bq' as unit. The metadata is then written in the `path/spect.nii.gz.json` file. If the json file already exist, it fails (you need to use the overwrite option). For some image types, such as SPECT or PET, the unit is required, while it is not the case for CT (always HU). Image types are : SPECT, PET, CT, Dose, ROI.

To READ a metadata image:

```python
import rpt_dosi.images as rim
image = rim.read_metaimage("path/spect.nii.gz")
print(image.info())
```

This script read the image and the associated metadata (fails if it does not exist). Use the option `read_header_only` to, well, read only the header of the image and not the whole content in memory. When you expect on given image type, you can use the following shortcuts that will read images and check there are of the required type:

```python
import rpt_dosi.images as rim
spect = rim.read_spect("path/spect.nii.gz")
ct = rim.read_ct("path/ct.nii.gz")
spect2 = rim.read_spect("path/spect.nii.gz", 'Bq')
```

If the unit is required (like for SPECT) and there is no metadata associated, it fails. You can however set the unit in the read command like for the `spect2`: unit will be converted (or set if not exist) to Bq.

The classes are `MetaImageSPECT`, `MetaImageCT`, etc. See examples below: 

```python
import rpt_dosi.images as rim
spect = rim.MetaImageSPECT("path/spect.nii.gz", read_header_only=True, create=True, unit='Bq')
```




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
  Updates SPECT image content, allowing conversion to different units and scaling of pixel values. The metadata are still stored in a file called `updated_image.nii.gz.json`. 

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
  rpt_image_info path/to/image.mhd
  ```

### Python functions and classes for images handling

In the toolkit, classes such as ImageBase, ImageSPECT, and others form a structured approach to handle different types of medical images. ImageBase acts as a foundational class providing common attributes and methods applicable across various image types. Derived from this base, ImageSPECT specializes in handling SPECT images, incorporating specific attributes for units like Bq or Bq/ml and methods tailored to SPECT's unique processing requirements. 

The following functions are designed to perform advanced computations and transformations on the imaging data.

- **read_spect**
  Loads SPECT imaging data into the toolkit for processing.

  **Usage example:**
  ```
  import rpt_dosi.images as rim
  spect = rim.read_spect('path/to/spect_file.mhd')
  ```

- **compute_total_activity()**
  Calculates the total radioactive activity within a SPECT image.

  **Usage example:**
  ```
  total_activity = spect.compute_total_activity()
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