from . import utils as rhe
from . import metadata as rmd
from .utils import fatal, convert_datetime, compare_dict
import SimpleITK as sitk
import math
import numpy as np
import os
import click
import copy
import json
from box import BoxList, Box
import datetime
import shutil
from pathlib import Path


def read_metaimage(file_path, reading_mode="image"):
    """
    Read an existing metaimage.
    Need both the image and the associated metadata json sidecar file.

    reading_mode:
    - image
    - header_only
    - metadata_only

    """
    if not os.path.exists(file_path):
        fatal(f"read_metaimage: {file_path} does not exist")
    image_type = read_metaimage_type_from_metadata(file_path)
    if image_type is None:
        # print(f"read_metaimage: {file_path} is not a metaimage")
        pass
    # create the correct class if it is found
    the_class = get_metaimage_class_from_type(image_type)
    im = the_class(file_path, reading_mode=reading_mode, create=False)
    return im


def metadata_exists(file_path):
    json_path = str(file_path) + ".json"
    return os.path.exists(json_path)


def new_metaimage(
    image_type, file_path, overwrite=False, reading_mode="metadata_only", **kwargs
):
    """
    Create (and read) a new metaimage.
    The filepath of the image must exist.
    The associated metadata json sidecar file is created (or overwritten if already exist)
    The required parameters must be given for some image_type :
    - SPECT require 'unit'
    - ROI require 'name'
    """
    the_class = get_metaimage_class_from_type(image_type)
    if overwrite:
        delete_image_metadata(file_path)
    output = the_class(file_path, reading_mode=reading_mode, create=True, **kwargs)
    return output


def get_metaimage_class_from_type(image_type):
    if image_type not in image_builders:
        fatal(
            f"This image type '{image_type}' is not known. "
            f"Known image types: {image_builders.keys()}"
        )
    the_class = image_builders[image_type]
    return the_class


def read_metaimage_type_from_metadata(file_path):
    json_path = str(file_path) + ".json"
    if not os.path.exists(json_path):
        return None
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        if "image_type" not in data:
            fatal(f"No image type in metadata {json_path}")
    except:
        fatal(f"Could not read image metadata file {json_path}. Not a json ?")
    return data["image_type"]


def delete_image_metadata(file_path):
    f = str(file_path) + ".json"
    if os.path.exists(f):
        os.remove(f)


def read_ct(filepath):
    """
    Read or create a CT image
    """
    image_type = read_metaimage_type_from_metadata(filepath)
    if image_type is None:
        ct = new_metaimage("CT", filepath, overwrite=False, reading_mode="image")
    else:
        if image_type == "CT":
            ct = read_metaimage(filepath, reading_mode="image")
        else:
            fatal(f"Error while reading, this is not a CT image: {filepath}")
    return ct


def read_spect(filepath, unit=None):
    """
    Read or create a SPECT image and consider the given unit
    """
    image_type = read_metaimage_type_from_metadata(filepath)
    spect = None
    if image_type is None:
        spect = new_metaimage(
            "SPECT", filepath, overwrite=False, reading_mode="image", unit=unit
        )
    else:
        if image_type == "SPECT":
            spect = read_metaimage(filepath, reading_mode="image")
        else:
            fatal(f"Error while reading, this is not a SPECT image: {filepath}")
    if unit is not None:
        spect.convert_to_unit(unit)
    return spect


def read_pet(filepath, unit=None):
    """
    Read or create a PET image and consider the given unit
    """
    image_type = read_metaimage_type_from_metadata(filepath)
    pet = None
    if image_type is None:
        pet = new_metaimage(
            "PET", filepath, overwrite=False, reading_mode="image", unit=unit
        )
    else:
        if image_type == "PET":
            pet = read_metaimage(filepath, reading_mode="image")
        else:
            fatal(f"Error while reading, this is not a PET image: {filepath}")
    if unit is not None:
        pet.convert_to_unit(unit)
    return pet


def read_roi(filepath, name=None, effective_time_h=None):
    """
    Read or create a ROI image and consider the given unit
    """
    image_type = read_metaimage_type_from_metadata(filepath)
    roi = None
    if image_type is None:
        roi = new_metaimage(
            "ROI", filepath, overwrite=False, reading_mode="image", name=name
        )
    else:
        if image_type == "ROI":
            roi = read_metaimage(filepath, reading_mode="image")
        else:
            fatal(f"Error while reading, this is not a ROI image: {filepath}")
        if name is not None:
            roi.name = name
    if effective_time_h is not None:
        roi.effective_time_h = effective_time_h
    return roi


def read_dose(filepath, unit=None):
    """
    Read or create a Dose image and consider the given unit
    """
    image_type = read_metaimage_type_from_metadata(filepath)
    if image_type is None:
        dose = new_metaimage(
            "Dose", filepath, overwrite=False, reading_mode="image", unit=unit
        )
    else:
        if image_type == "Dose":
            dose = read_metaimage(filepath, reading_mode="image")
        else:
            fatal(f"Error while reading, this is not a Dose image: {filepath}")
    if unit is not None:
        dose.convert_to_unit(unit)
    return dose


def read_list_of_rois(filename, folder=None):
    rois = []
    with open(filename, "r") as f:
        rois_file = BoxList(json.load(f))
        for roi in rois_file:
            Teff = None
            if "time_eff_h" in roi:  # FIXME change to effective_time_h ?
                Teff = roi["time_eff_h"]
            fn = roi.roi_filename
            if folder is not None:
                fn = os.path.join(folder, fn)
            r = read_roi(fn, roi.roi_name, Teff)
            rois.append(r)
    return rois


class MetaImageBase(rmd.ClassWithMetaData):
    authorized_units = []
    unit_default_values = {}
    image_type = None
    unit_converter = {}

    # the metadata members are attributes that will be
    # stored/loaded on disk (in json file)
    _metadata_fields = {
        "image_type": str,
        "description": str,
        "filename": str,
        "body_weight_kg": float,
        "acquisition_datetime": str,
        "unit": str,
    }

    def __init__(self, image_path, reading_mode, create=False, **kwargs):
        super().__init__()
        # init
        self.image = None
        # metadata infos
        self.description = ""
        self._acquisition_datetime = None
        self.body_weight_kg = None
        # internal parameters
        self._image_filename = None
        self._image_file_path = None
        self._image_header = None
        self._unit = None
        self._unit_default_value = 0
        self.image_file_path = image_path
        # check filename
        if not os.path.exists(image_path):
            fatal(f"Cannot create a MetaImage, {image_path} does not exist")
        # special case to create the metadata if it does not exist
        if not os.path.exists(self.metadata_file_path) and create:
            self._init_required_metadata(**kwargs)
        # read metadata
        if reading_mode not in ["metadata_only", "image", "header_only"]:
            fatal(
                f"Reading mode {reading_mode} not recognized, should be "
                f'either "metadata_only" or "image" or "header_only"'
            )
        if reading_mode == "metadata_only":
            self.read_metadata()
        if reading_mode == "header_only":
            self.read_metadata()
            self.read_image_header()
        if reading_mode == "image":
            self.read()
        return

    def _init_required_metadata(self, **kwargs):
        # specific required metadata for this image type
        pass

    def ensure_image_is_loaded(self):
        if self.image is None:
            fatal(f"Image {self} has not been loaded")
        if not isinstance(self.image, sitk.Image):
            fatal(
                f"Image {self} has not been correctly loaded, this is not a SITK image"
            )
        return True

    def image_is_loaded(self):
        if self.image is None:
            return False
        if not isinstance(self.image, sitk.Image):
            return False
        return True

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value):
        """
        Only change the unit when it is not known (equal to None).
        Otherwise, user "convert"
        """
        if value == self._unit:
            return
        if self._unit is not None:
            fatal(
                f"Cannot set the unit to '{value}' while it is "
                f"'{self.unit}' use convert_to_unit ({self})"
            )
        if value is None:
            return
        if self.image_type is None:
            fatal(
                "Cannot set the unit, the image type is not known "
                f"(use change_image_type function, with one "
                f"of {[k for k in image_builders]})"
            )
        if len(self.authorized_units) < 1 and value not in self.authorized_units:
            fatal(f"Unauthorized unit {value}. Must be one of {self.authorized_units}")
        if self._unit is not None:
            fatal(
                f"Cannot set the unit to {value} (current value is {self._unit})"
                f" ; Use convert functions or delete metadata"
            )
        self._unit = value
        if value in self.unit_default_values:
            self._unit_default_value = self.unit_default_values[value]

    @property
    def image_file_path(self):
        return self._image_file_path

    @image_file_path.setter
    def image_file_path(self, value):
        self._image_file_path = os.path.abspath(value)
        self._image_filename = os.path.basename(value)

    @property
    def filename(self):
        return self._image_filename

    @filename.setter
    def filename(self, value):
        self._image_filename = os.path.basename(value)
        self._image_file_path = os.path.abspath(value)

    def require_unit(self, unit):
        if unit != self.unit:
            fatal(f"The unit '{unit}' is required while it is {self.unit}")

    def convert_to_unit(self, new_unit):
        if self.unit == new_unit:
            return
        if self.unit is None:
            self._unit = new_unit
            return
        if new_unit not in self.unit_converter:
            fatal(
                f"I dont know how to convert to the unit to '{new_unit}' "
                f"(current unit is {self.unit}, available units are {self.authorized_units}"
                f" ; maybe set the image type ?)"
            )
        # get the function's name
        f = self.unit_converter[new_unit]
        # and call it (probably there is a better way)
        getattr(self, f)()

    @property
    def voxel_volume_cc(self):
        self.ensure_image_is_loaded()
        v = np.prod(self.image.GetSpacing()) / 1000
        return v

    @property
    def voxel_volume_ml(self):
        return self.voxel_volume_cc()

    @property
    def unit_default_value(self):
        return self._unit_default_value

    @property
    def acquisition_datetime(self):
        return self._acquisition_datetime

    @acquisition_datetime.setter
    def acquisition_datetime(self, value):
        if value is None:
            self._acquisition_datetime = None
            return
        self._acquisition_datetime = convert_datetime(value)

    def read(self, file_path=None):
        if file_path is not None:
            self.image_file_path = file_path
        if not os.path.exists(self.image_file_path):
            fatal(f"Image: the filename {self.image_file_path} does not exist.")
        self.image = sitk.ReadImage(self.image_file_path)
        self.read_metadata()

    def write(self, file_path=None, writing_mode="image"):
        if file_path is None:
            file_path = self.image_file_path
            if file_path is None:
                fatal(f"Provide the file_path to write the image to.")
        if os.path.dirname(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.image_file_path = file_path
        if writing_mode == "image":
            if not self.image_is_loaded():
                self.read()
            sitk.WriteImage(self.image, file_path)
        else:
            if writing_mode != "metadata_only":
                fatal(
                    f'Cannot write the image to {writing_mode}, must be "image" or "metadata_only"'
                )
        self.write_metadata()

    def read_metadata(self):
        json_filename = self.metadata_file_path
        current_image_type = self.image_type
        p = self.image_file_path
        if not os.path.exists(json_filename):
            return
        # unit can only be set if it is None
        self._unit = None
        self.load_from_json(json_filename)
        # else:
        #    fatal(f'Error: no metadata file {json_filename}"')
        # put back image path and check image filename
        read_filename = self._image_filename
        self.image_file_path = p
        if self._image_filename != read_filename:
            fatal(
                f'Error: the filename in the sidecar json is "{read_filename}" '
                f'while we expected "{self.filename}"'
            )
        if self.image_type != current_image_type:
            fatal(
                f'Image type is "{current_image_type}" but reading '
                f'metadata "{self.image_type}" in the file {json_filename}'
            )

    def read_image_header(self):
        reader = sitk.ImageFileReader()
        reader.SetFileName(str(self.image_file_path))
        reader.LoadPrivateTagsOn()
        reader.ReadImageInformation()
        self._image_header = Box()
        self._image_header.size = reader.GetSize()
        self._image_header.spacing = reader.GetSpacing()
        self._image_header.origin = reader.GetOrigin()
        self._image_header.pixel_type = sitk.GetPixelIDValueAsString(
            reader.GetPixelID()
        )

    def write_metadata(self):
        json_filename = self.metadata_file_path
        self.save_to_json(json_filename)

    @property
    def metadata_file_path(self):
        if self.image_file_path is not None:
            return str(self.image_file_path) + ".json"
        return None

    def info(self):
        s = super().info()
        json_filename = self.metadata_file_path
        w = self._info_width
        js = f'{"metadata":<{w}}: {self.metadata_file_path})'
        if json_filename is not None and not os.path.exists(json_filename):
            js = f'{"metadata":<{w}}: no metadata'
        s += f'{"Loaded?":<{w}}: {self.image_is_loaded()}\n'
        s = f"{js}\n{s}"
        if self.image_is_loaded():
            s += f'{"Size":<{w}}: {self.image.GetSize()}\n'
            s += f'{"Spacing":<{w}}: {self.image.GetSpacing()}\n'
            s += f'{"Origin":<{w}}: {self.image.GetOrigin()}\n'
            s += f'{"Pixel":<{w}}: {sitk.GetPixelIDValueAsString(self.image.GetPixelID())}'
        else:
            if self._image_header is not None:
                s += f'{"Size":<{w}}: {self._image_header.size}\n'
                s += f'{"Spacing":<{w}}: {self._image_header.spacing}\n'
                s += f'{"Origin":<{w}}: {self._image_header.origin}\n'
                s += f'{"Pixel":<{w}}: {self._image_header.pixel_type}'
        return s.strip("\n")

    def check_file_metadata(self):
        # get the current metadata
        memory_dict = self.to_dict()
        # read the metadata in the file
        try:
            im = read_metaimage(self.image_file_path)
            disk_dict = im.to_dict()
            # compare
            ok, msg = compare_dict(memory_dict, disk_dict)
        except Exception as e:
            ok = False
            msg = f"Error while reading {e}"
        if msg != "":
            msg = f"{self._image_filename} metadata error : {msg}"
        return ok, msg


class MetaImageCT(MetaImageBase):
    authorized_units = ["HU", "g/cm3"]  # FIXME separate attenuation
    unit_default_values = {"HU": -1000, "g/cm3": 0}
    image_type = "CT"

    def __init__(self, image_path, reading_mode, create=False, **kwargs):
        super().__init__(image_path, reading_mode, create, **kwargs)
        # must set the unit after to get the unit_default_values right
        self.unit = "HU"

    def compute_densities(self):  # FIXME to remove ?
        if self.unit != "HU":
            fatal(f"Unit {self.unit} is not HU, cannot compute density CT")
        density_ct = copy.copy(self)
        density_ct._unit = "g/cm3"
        # Simple conversion from HU to g/cm^3
        density_ct.image = self.image / 1000 + 1
        # the density of air is near 0, not negative
        a = sitk.GetArrayFromImage(density_ct.image)
        a[a < 0] = 0
        density_ct.image = sitk.GetImageFromArray(a)
        density_ct.image.CopyInformation(self.image)
        return density_ct


class MetaImageSPECT(MetaImageBase):
    authorized_units = ["Bq", "Bq/mL", "SUV"]
    unit_default_values = {"Bq": 0, "Bq/mL": 0, "SUV": 0}
    image_type = "SPECT"
    unit_converter = {
        "Bq": "convert_to_bq",
        "Bq/mL": "convert_to_bqml",
        "SUV": "convert_to_suv",
    }

    _metadata_fields = {
        **MetaImageBase._metadata_fields,  # Inherit base class fields
        "injection_datetime": str,
        "injection_activity_mbq": float,
    }

    def __init__(self, image_path, reading_mode, create=False, **kwargs):
        # metadata
        self._injection_datetime = None
        self.injection_activity_mbq = None
        super().__init__(image_path, reading_mode, create, **kwargs)

    def _init_required_metadata(self, **kwargs):
        if "unit" not in kwargs:
            fatal(f"Unit is required to create a MetaImageSPECT")
        if kwargs["unit"] not in self.authorized_units:
            fatal(
                f'Unit for MetaImageSPECT must be in {self.authorized_units}, while it is {kwargs["unit"]}. Please provide the units'
            )
        self._unit = kwargs["unit"]

    @property
    def injection_datetime(self):
        return self._injection_datetime

    @injection_datetime.setter
    def injection_datetime(self, value):
        if value is None:
            self._injection_datetime = None
            return
        self._injection_datetime = convert_datetime(value)

    def info(self):
        s = super().info() + "\n"
        w = self._info_width
        s += f'{"Injection date:":{w}}: {self.injection_datetime}\n'
        s += f'{"Injection:":{w}}: {self.injection_activity_mbq} MBq\n'
        if self.image_is_loaded():
            s += f'{"Total activity:":{w}}: {self.compute_total_activity()} MBq'
        else:
            s += f'{"Total activity:":{w}}: (image not loaded)'
        return s

    def convert_to_bq(self):
        self.ensure_image_is_loaded()
        if self.unit == "Bq/mL":
            self.image *= self.voxel_volume_cc
        if self.unit == "SUV":
            self.image *= self.voxel_volume_cc * (
                self.injection_activity_mbq / self.body_weight_kg
            )
        self._unit = "Bq"

    def convert_to_bqml(self):
        if self.unit == "Bq":
            self.ensure_image_is_loaded()
            # need to cast when divide
            self.image = sitk.Cast(self.image, sitk.sitkFloat64)
            self.image /= self.voxel_volume_cc
        if self.unit == "SUV":
            self.convert_to_bq()
            self.convert_to_bqml()
        self._unit = "Bq/mL"

    def convert_to_suv(self):
        if self.body_weight_kg is None:
            fatal(
                f"To convert to SUV, body_weight_kg cannot be None (SPECT image {self._image_filename})"
            )
        if self.injection_activity_mbq is None:
            fatal(
                f"To convert to SUV, injection_activity_MBq cannot be None (SPECT image {self._image_filename})"
            )
        # convert to Bq/mL first then SUV
        self.convert_to_bqml()
        self.image /= self.injection_activity_mbq / self.body_weight_kg
        self._unit = "SUV"

    def compute_total_activity(self):
        self.ensure_image_is_loaded()
        if self.unit is None:
            fatal(f"Cannot compute total activity without unit, in image {self}")
        if self.image is None:
            fatal("Cannot compute total activity, the image data not loaded.")
        if self.unit == "Bq":
            arr = sitk.GetArrayViewFromImage(self.image)
            total_activity = np.sum(arr)
            return total_activity
        else:
            u = self.unit
            self.convert_to_bq()
            t = self.compute_total_activity()
            self.convert_to_unit(u)
            return t

    @property
    def time_from_injection_h(self):
        return get_time_from_injection_h(
            self.injection_datetime, self.acquisition_datetime
        )

    @time_from_injection_h.setter
    def time_from_injection_h(self, value):
        self.injection_datetime, self.acquisition_datetime = set_time_from_injection_h(
            self.injection_datetime, self.acquisition_datetime, value
        )

    def write_metadata(self):
        if self.unit is None:
            fatal(
                f"Cannot write metadata for this {self.image_type} image, unit is None ({self})"
            )
        super().write_metadata()


class MetaImagePET(MetaImageSPECT):
    authorized_units = ["Bq/mL", "SUV"]
    unit_default_values = {"Bq/mL": 0, "SUV": 0}
    image_type = "PET"

    def __init__(self, image_path, reading_mode, create=False, **kwargs):
        # metadata
        self._injection_datetime = None
        self.injection_activity_mbq = None
        super().__init__(image_path, reading_mode, create, **kwargs)

    def _init_required_metadata(self, **kwargs):
        if "unit" not in kwargs:
            fatal(f"Unit is required to create a MetaImagePET")
        if kwargs["unit"] not in self.authorized_units:
            fatal(
                f'Unit for MetaImagePET must be in {self.authorized_units}, while it is {kwargs["unit"]}'
            )
        self._unit = kwargs["unit"]


class MetaImageROI(MetaImageBase):
    authorized_units = ["label"]
    unit_default_values = {"label": 0}
    image_type = "ROI"

    _metadata_fields = {
        **MetaImageBase._metadata_fields,  # Inherit base class fields
        "name": str,
        "effective_time_h": float,
    }

    def __init__(self, image_path, reading_mode, create=False, **kwargs):
        self.name = None
        self._unit = "label"
        self.effective_time_h = None
        self.mass_g = None
        self.volume_cc = None
        super().__init__(image_path, reading_mode, create, **kwargs)

    def _init_required_metadata(self, **kwargs):
        if "name" not in kwargs:
            fatal(f"Name is required to create a MetaImageROI")
        self.name = kwargs["name"]

    def info(self):
        w = self._info_width
        s = super().info() + "\n"
        s += f'{"mass_g":<{w}}: {self.mass_g} g\n'
        s += f'{"volume_cc":<{w}}: {self.volume_cc} cc'
        return s

    def update_mass_and_volume(self, density_ct):
        self.ensure_image_is_loaded()
        # compute mass
        a = sitk.GetArrayViewFromImage(self.image)
        da = sitk.GetArrayViewFromImage(density_ct.image)
        d = da[a == 1]
        self.mass_g = np.sum(d) * self.voxel_volume_cc
        self.volume_cc = len(d) * self.voxel_volume_cc

    def write_metadata(self):
        if self.name is None:
            fatal(f"Cannot write metadata for this ROI image, name is None ({self})")
        super().write_metadata()


class MetaImageDose(MetaImageSPECT):
    authorized_units = ["Gy", "Gy/s"]
    unit_default_values = {"Gy": 0, "Gy/s": 0}
    image_type = "Dose"

    def __init__(self, image_path, reading_mode, create=False, **kwargs):
        super().__init__(image_path, reading_mode, create, **kwargs)

    def _init_required_metadata(self, **kwargs):
        if "unit" not in kwargs:
            fatal(f"Unit is required to create a MetaImageDose")
        self._unit = kwargs["unit"]


image_builders = {
    None: MetaImageBase,
    "CT": MetaImageCT,
    "SPECT": MetaImageSPECT,
    "PET": MetaImagePET,
    "ROI": MetaImageROI,
    "Dose": MetaImageDose,
}


def images_have_same_domain(image1, image2, tolerance=1e-5):
    # Check if the sizes and origins of the images are the same,
    # and if the spacing values are close within the given tolerance
    is_same = (
        len(image1.GetSize()) == len(image2.GetSize())
        and all(i == j for i, j in zip(image1.GetSize(), image2.GetSize()))
        and images_have_same_spacing(image1, image2, tolerance)
        and all(
            math.isclose(i, j, rel_tol=tolerance)
            for i, j in zip(image1.GetOrigin(), image2.GetOrigin())
        )
    )
    return is_same


def validate_spacing(ctx, param, value):
    if len(value) == 1:
        # If only one value is provided, duplicate it three times
        return value[0], value[0], value[0]
    elif len(value) == 3:
        # If three values are provided, use them as-is
        return value
    else:
        # Raise an error if any number of values other than 1 or 3 are provided
        raise click.BadParameter("Spacing must be either one or three values")


def images_have_same_spacing(image1, image2, tolerance=1e-5):
    # Check if the spacing values are close within the given tolerance
    is_same = all(
        math.isclose(i, j, rel_tol=tolerance)
        for i, j in zip(image1.GetSpacing(), image2.GetSpacing())
    )
    return is_same


def image_has_this_spacing(image1, spacing, tolerance=1e-5):
    # Check if the spacing values are close within the given tolerance
    is_same = all(
        math.isclose(i, j, rel_tol=tolerance)
        for i, j in zip(image1.GetSpacing(), spacing)
    )
    return is_same


def resample_itk_image_like(img, like_img, default_pixel_value, linear):
    # Create a resampler object
    resampler = sitk.ResampleImageFilter()

    # Set the resampler parameters from img1
    resampler.SetSize(like_img.GetSize())
    resampler.SetOutputSpacing(like_img.GetSpacing())
    resampler.SetOutputOrigin(like_img.GetOrigin())
    resampler.SetOutputDirection(like_img.GetDirection())
    resampler.SetDefaultPixelValue(default_pixel_value)

    # Use the identity transform - we only resample in place
    resampler.SetTransform(sitk.Transform())

    # Set the interpolation method to Linear
    if linear:
        resampler.SetInterpolator(sitk.sitkLinear)

    # Execute the resampling
    resampled_img = resampler.Execute(img)

    return resampled_img


def resample_itk_image_spacing(img, new_spacing, default_pixel_value, linear):
    # Create a resampler object
    resampler = sitk.ResampleImageFilter()

    # new size
    dim = img.GetDimension()
    original_size = img.GetSize()
    original_spacing = img.GetSpacing()
    new_size = [
        int(round(osz * ospc / nspc))
        for osz, ospc, nspc in zip(original_size, original_spacing, new_spacing)
    ]

    # Set the resampler parameters from img1
    resampler.SetSize(new_size)
    resampler.SetOutputSpacing(new_spacing)
    resampler.SetOutputOrigin(img.GetOrigin())
    resampler.SetOutputDirection(img.GetDirection())
    resampler.SetDefaultPixelValue(default_pixel_value)

    # Use the identity transform - we only resample in place
    resampler.SetTransform(sitk.Transform())

    # Set the interpolation method to Linear
    if linear:
        resampler.SetInterpolator(sitk.sitkLinear)

    # Execute the resampling
    resampled_img = resampler.Execute(img)

    return resampled_img


def image_set_background(ct, roi, bg_value=-1000, roi_bg_value=0):
    if not images_have_same_domain(ct, roi):
        fatal(
            f"Cannot set_background for images, the sizes are different"
            f" : {ct.GetSize()} {ct.GetSpacing()} vs {roi.GetSize()} {roi.GetSpacing()}"
        )
    # get as array
    cta = sitk.GetArrayFromImage(ct)
    bga = sitk.GetArrayFromImage(roi)
    # set bg
    cta[bga == roi_bg_value] = bg_value
    # back to itk image
    cto = sitk.GetImageFromArray(cta)
    cto.CopyInformation(ct)
    return cto


def crop_to_bounding_box(img, bg_value=-1000):
    # Create a binary version of the image (1 where img is not 0, else 0)
    tiny = 1
    binary = sitk.BinaryThreshold(
        img,
        lowerThreshold=bg_value + tiny,
        upperThreshold=1e10,
        insideValue=1,
        outsideValue=0,
    )

    # Create a shape statistics object and execute it on the binary image
    shape_stats = sitk.LabelShapeStatisticsImageFilter()
    shape_stats.Execute(binary)

    # Get bounding box (you can also add checks here to make sure there is only one label)
    bounding_box = shape_stats.GetBoundingBox(1)

    # Create a region of interest filter and set its region to the bounding box
    roi_filter = sitk.RegionOfInterestImageFilter()
    roi_filter.SetRegionOfInterest(bounding_box)

    # Execute filter on original image
    cropped_img = roi_filter.Execute(img)

    return cropped_img


def convert_ct_to_densities(ct):
    # Simple conversion from HU to g/cm^3
    densities = ct / 1000 + 1
    # the density of air is near 0, not negative
    densities[densities < 0] = 0
    return densities


def apply_itk_gauss_smoothing(img, sigma):
    if sigma is None:
        return img
    if sigma == "auto" or sigma == 0:
        sigma = [0.5 * sp for sp in img.GetSpacing()]
    gauss_filter = sitk.SmoothingRecursiveGaussianImageFilter()
    gauss_filter.SetSigma(sigma)
    gauss_filter.SetNormalizeAcrossScale(True)
    return gauss_filter.Execute(img)


def resample_ct_like(ct: MetaImageCT, like: MetaImageBase, gaussian_sigma=None):
    if images_have_same_domain(ct.image, like.image):
        return ct
    o = copy.copy(ct)
    o.image = apply_itk_gauss_smoothing(ct.image, gaussian_sigma)
    o.image = resample_itk_image_like(
        o.image, like.image, o.unit_default_value, linear=True
    )
    return o


def resample_dose_like(dose: MetaImageDose, like: MetaImageBase, gaussian_sigma=None):
    if images_have_same_domain(dose.image, like.image):
        return dose
    o = copy.copy(dose)
    o.image = apply_itk_gauss_smoothing(dose.image, gaussian_sigma)
    o.image = resample_itk_image_like(
        o.image, like.image, o.unit_default_value, linear=True
    )
    return o


def resample_ct_spacing(ct: MetaImageCT, spacing, gaussian_sigma=None):
    if image_has_this_spacing(ct.image, spacing):
        return
    o = copy.copy(ct)
    o.image = apply_itk_gauss_smoothing(ct.image, gaussian_sigma)
    o.image = resample_itk_image_spacing(
        o.image, spacing, o.unit_default_value, linear=True
    )
    return o


def resample_spect_like(
    spect: MetaImageSPECT, like: MetaImageBase, gaussian_sigma=None
):
    if images_have_same_domain(spect.image, like.image):
        return spect
    o = copy.copy(spect)
    o.image = apply_itk_gauss_smoothing(spect.image, gaussian_sigma)
    # convert to bqml and back to initial unit
    initial_unit = o.unit
    o.convert_to_bqml()
    o.image = resample_itk_image_like(
        o.image, like.image, o.unit_default_value, linear=True
    )
    o.convert_to_unit(initial_unit)
    return o


def resample_spect_spacing(spect: MetaImageSPECT, spacing, gaussian_sigma=None):
    if image_has_this_spacing(spect.image, spacing):
        return
    if not spect.image_is_loaded():
        spect.read()
    o = copy.copy(spect)
    o.image = apply_itk_gauss_smoothing(spect.image, gaussian_sigma)
    # convert to bqml and back to initial unit
    initial_unit = o.unit
    o.convert_to_bqml()
    o.image = resample_itk_image_spacing(
        o.image, spacing, o.unit_default_value, linear=True
    )
    o.convert_to_unit(initial_unit)
    # take the volume into account if needed
    return o


def resample_roi_like(roi: MetaImageROI, like: MetaImageBase):
    if images_have_same_domain(roi.image, like.image) and images_have_same_spacing(
        roi.image, like.image
    ):
        return roi
    o = copy.copy(roi)
    o.image = resample_itk_image_like(
        roi.image, like.image, o.unit_default_value, linear=False
    )
    return o


def resample_roi_spacing(roi: MetaImageROI, spacing):
    if image_has_this_spacing(roi.image, spacing):
        return
    o = copy.copy(roi)
    o.image = resample_itk_image_spacing(
        o.image, spacing, o.unit_default_value, linear=False
    )
    return o


def test_compare_images(image1, image2, tol=1e-6):
    img1 = sitk.ReadImage(image1)
    img2 = sitk.ReadImage(image2)
    if not images_have_same_domain(img1, img2):
        print(f"Im1: {img1.GetSize()}  {img1.GetSpacing()}   {img1.GetOrigin()}")
        print(f"Im2: {img2.GetSize()}  {img2.GetSpacing()}   {img2.GetOrigin()}")
        return False
    # warning : strange behavior with GetArrayViewFromImage ???
    img1 = sitk.GetArrayFromImage(img1)
    img2 = sitk.GetArrayFromImage(img2)
    ok = np.allclose(img1, img2, atol=tol)
    if not ok:
        print(f"Total image1 = {np.sum(img1)}")
        print(f"Total image2 = {np.sum(img2)}")
    return ok


def dilate_mask(img, dilatation_mm):
    # convert radius in vox
    radius = [
        int(round(dilatation_mm / img.GetSpacing()[0])),
        int(round(dilatation_mm / img.GetSpacing()[1])),
        int(round(dilatation_mm / img.GetSpacing()[2])),
    ]
    # Set the kernel element
    dilate_filter = sitk.BinaryDilateImageFilter()
    dilate_filter.SetKernelRadius(radius)
    dilate_filter.SetKernelType(sitk.sitkBall)
    dilate_filter.SetForegroundValue(1)
    output = dilate_filter.Execute(img)
    return output


def mip(img, dim3=False):
    f = sitk.MaximumProjectionImageFilter()
    f.SetProjectionDimension(1)

    # Compute the MIP along dimension 1
    mip_slice = f.Execute(img)

    if dim3:
        # Convert the MIP slice to a NumPy array
        mip_array = sitk.GetArrayFromImage(mip_slice)

        # Duplicate the MIP slice along dimension 1
        num_slices = img.GetSize()[1]
        mip_stack = np.tile(mip_array, (1, num_slices, 1))

        # Convert the NumPy array back to a SimpleITK image
        mip_image = sitk.GetImageFromArray(mip_stack)
        mip_image.CopyInformation(img)
    else:
        mip_image = mip_slice

    return mip_image


def image_roi_stats(roi, spect, ct=None, resample_like="spect"):
    # resample
    m = {"spect": spect, "roi": roi}
    if ct is not None:
        m["ct"] = ct
    if resample_like not in m:
        fatal(f"the option resample_like, must be {m}, while it is {resample_like}")
    resample_like = m[resample_like]

    if not spect.image_is_loaded():
        spect.read()
        spect.convert_to_bq()
    if not roi.image_is_loaded():
        roi.read()

    spect = resample_spect_like(spect, resample_like)
    roi = resample_roi_like(roi, resample_like)

    # convert to np
    spect_a = sitk.GetArrayViewFromImage(spect.image)
    roi_a = sitk.GetArrayViewFromImage(roi.image)

    # select pixels
    d = roi_a == 1
    p = spect_a[d]

    # compute stats
    res = {
        "mean": float(np.mean(p)),
        "std": float(np.std(p)),
        "min": float(np.min(p)),
        "max": float(np.max(p)),
        "sum": float(np.sum(p)),
        "volume_cc": float(len(p) * roi.voxel_volume_cc),
    }

    # for ct (densities)
    if ct is not None:
        if not ct.image_is_loaded():
            ct.read()
        ct = resample_ct_like(ct, resample_like)
        densities = ct.compute_densities()
        roi.update_mass_and_volume(densities)
        res["mass_g"] = roi.mass_g

    return Box(res)


def mhd_find_raw_file(mhd_file_path):
    with open(mhd_file_path, "r") as mhd_file:
        for line in mhd_file:
            if line.startswith("ElementDataFile"):
                return line.split("=")[1].strip()


def mhd_replace_raw(mhd_file_path, new_raw_filename):
    new_raw_filename = new_raw_filename.replace(".gz", "")
    with open(mhd_file_path, "r") as file:
        lines = file.readlines()
    with open(mhd_file_path, "w") as file:
        for line in lines:
            if line.startswith("ElementDataFile"):
                file.write(f"ElementDataFile = {new_raw_filename}\n")
            else:
                file.write(line)


def is_mhd_file(file_path):
    _, extension = rhe.get_basename_and_extension(file_path)
    return extension.lower() == ".mhd"


def mhd_copy_or_move(mhd_path, new_mhd_path, mode="copy"):
    # get the raw file
    folder = Path(os.path.dirname(mhd_path))
    raw_path = folder / mhd_find_raw_file(mhd_path)
    # do it
    if mode == "copy":
        shutil.copy(mhd_path, new_mhd_path)
    if mode == "move":
        shutil.move(mhd_path, new_mhd_path)
    # look for the correct raw path
    new_raw_path, _ = rhe.get_basename_and_extension(new_mhd_path)
    _, extension = rhe.get_basename_and_extension(raw_path)
    new_raw_path = Path(os.path.dirname(new_mhd_path)) / (new_raw_path + extension)
    # special case if raw.gz
    if not os.path.exists(raw_path):
        raw_path = Path(str(raw_path) + ".gz")
        new_raw_path = Path(str(new_raw_path) + ".gz")
    # copy the raw file
    # change the raw filename in the mhd file
    new_raw_filename = os.path.basename(new_raw_path)
    # do it
    if mode == "copy":
        shutil.copy(raw_path, new_raw_path)
        mhd_replace_raw(new_mhd_path, new_raw_filename)
        return
    if mode == "move":
        shutil.move(raw_path, new_raw_path)
        mhd_replace_raw(new_mhd_path, new_raw_filename)
        return
    print(
        f"Copy {mhd_path} + {os.path.basename(raw_path)} "
        f"--->   {new_mhd_path} + {os.path.basename(new_raw_path)}"
    )


def copy_or_move_image(source_path, dest_path, mode):
    modes = ["move", "copy", "dry_run"]
    if mode not in modes:
        fatal(f'Unknown mode {mode}, available modes: {", ".join(modes)}')
    src_ext = os.path.splitext(source_path)[1]
    dest_ext = os.path.splitext(dest_path)[1]
    if src_ext != dest_ext:
        fatal(
            f"Cannot copy image, the extensions are different, source={source_path}, dest={dest_path}"
        )
    if is_mhd_file(source_path):
        return mhd_copy_or_move(source_path, dest_path, mode)
    if mode == "copy":
        shutil.copy(source_path, dest_path)
        # FIXME copy the json sidecar also ?
        return
    if mode == "move":
        shutil.move(source_path, dest_path)
        return
    print(f"(dry run) Copy {source_path}  --->   {dest_path}")


def get_time_from_injection_h(injection_datetime, acquisition_datetime):
    i_date = None
    a_date = None
    try:
        i_date = datetime.datetime.strptime(injection_datetime, "%Y-%m-%d %H:%M:%S")
    except Exception:
        fatal(
            f"Cannot get the time from injection since injection_datetime "
            f"is {injection_datetime} and cannot be interpreted"
        )
    try:
        a_date = datetime.datetime.strptime(acquisition_datetime, "%Y-%m-%d %H:%M:%S")
    except Exception:
        fatal(
            f"Cannot get the time from injection since acquisition_datetime "
            f"is {acquisition_datetime} and cannot be interpreted"
        )
    hours_diff = (a_date - i_date).total_seconds() / 3600
    return hours_diff


def set_time_from_injection_h(
    injection_datetime, acquisition_datetime, time_from_injection_h
):
    # fake injection date
    if injection_datetime is None and acquisition_datetime is None:
        injection_datetime = "1970-01-01 00:00:00"
        return set_time_from_injection_h(
            injection_datetime, acquisition_datetime, time_from_injection_h
        )
    # compute acquisition date
    if injection_datetime is None and acquisition_datetime is not None:
        d = datetime.datetime.strptime(acquisition_datetime, "%Y-%m-%d %H:%M:%S")
        injection_datetime = (
            d - datetime.timedelta(hours=time_from_injection_h)
        ).strftime("%Y-%m-%d %H:%M:%S")
        return injection_datetime, acquisition_datetime
    # compute injection date
    if injection_datetime is not None and acquisition_datetime is None:
        d = datetime.datetime.strptime(injection_datetime, "%Y-%m-%d %H:%M:%S")
        acquisition_datetime = (
            d + datetime.timedelta(hours=time_from_injection_h)
        ).strftime("%Y-%m-%d %H:%M:%S")
        return injection_datetime, acquisition_datetime
    # cannot do it
    fatal(
        f"Cannot set the time from injection since injection_datetime or acquisition_datetime exists: "
        f"inj={injection_datetime} acq={acquisition_datetime} time_from_inj={time_from_injection_h}"
    )
