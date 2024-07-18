
## Basic Image Manipulation with Associated Metadata (sidecar JSON file)

**Metadata** This section delves into handling and manipulating medical imaging data within the toolkit. The toolkit proposes functions and classes to manage images together with the associated **metadata** that are needed for dose computation (such as injected activity of acquisition time and image units: Bq, SUV, etc.). The metadata information are stored in a "sidecar" json file. 

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

This script read the image and the associated metadata (fails if it does not exist). Use the option `read_header_only` to, well, read only the header of the image and not the whole content in memory. 

When you expect on given image type, you can use the following shortcuts that will read images and check there are of the required type:

```python
import rpt_dosi.images as rim
spect = rim.read_spect("path/spect.nii.gz")
ct = rim.read_ct("path/ct.nii.gz")
spect2 = rim.read_spect("path/spect.nii.gz", 'Bq')
```

If the unit is required (like for SPECT) and there is no metadata associated, it fails. You can however set the unit in the read command like for the `spect2`: unit will be converted (or set if not exist) to Bq.

The classes are `MetaImageSPECT`, `MetaImageCT`, etc. See examples below:

```python
import
    rpt_dosi.images as rim

spect = rim.MetaImageSPECT(
    "path/spect.nii.gz",
    reading_mode=True,
    create=True,
    unit='Bq')
```

A instance of a metaimage contains some member functions such as the following:


```python
import rpt_dosi.images as rim
spect = rim.read_spect("path/spect.nii.gz")
spect.convert_to_bqml()
spect.body_weight_kg = 80
spect.convert_to_unit('SUV')
print('Total activity in the image', spect.compute_total_activity())
spect.acquisition_datetime = "2020 06 03 12:00"
spect.injection_datetime = "2020 06 03 10:00"
print(spect.info())
print(spect)
spect.write()
spect.write("this_is_a_copy.mhd")

# for a CT
ct = rim.read_spect("path/ct.nii.gz")
densitiy_image = ct.compute_densities()
```

