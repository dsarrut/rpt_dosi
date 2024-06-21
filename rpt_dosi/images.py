from . import helpers as rhe
from . import metadata as rmd
import SimpleITK as sitk
import math
from .helpers import fatal
import numpy as np
import os
import click
import copy
import json
from box import BoxList, Box
import datetime
import shutil
from pathlib import Path


def read_image(filename):
    # try to find the image type
    image_type = read_image_type_from_metadata(filename)
    if image_type is not None:
        # create the correct class if it is found
        im = build_image_from_type(image_type)
        im.read(filename)
    else:
        # else create a generic image
        im = ImageBase()
        im.read(filename)
    return im


def delete_metadata(filename):
    im = ImageBase()
    im._image_filename = filename
    f = im.get_metadata_filepath()
    os.remove(f)


def read_image_header_only(filepath):
    # try to find the image type
    image_type = read_image_type_from_metadata(filepath)
    if image_type is not None:
        # create the correct class if it is found
        im = build_image_from_type(image_type)
        im.image_path = filepath
        im.read_metadata()
    else:
        # else create a generic image
        im = ImageBase()
        im.image_path = filepath
        im.read_metadata()
    # read the image header (size, spacing, etc.)
    im.read_image_header()
    return im


def read_image_type_from_metadata(filepath):
    json_path = str(filepath) + ".json"
    if not os.path.exists(json_path):
        return None
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        if 'image_type' not in data:
            fatal(f'No image type in metadata {json_path}')
    except:
        fatal(f'Could not read image metadata file {json_path}. Not a json ?')
    return data['image_type']


def delete_image_metadata(filepath):
    im = ImageBase()
    im._image_path = filepath
    f = im.get_metadata_filepath()
    if os.path.exists(f):
        os.remove(f)


def build_image_from_type(image_type):
    if image_type not in image_builders:
        fatal(f"This image type '{image_type}' is not known. "
              f"Known image types: {image_builders.keys()}")
    the_class = image_builders[image_type]
    output = the_class()
    return output


def read_ct(filename):
    ct = ImageCT()
    ct.read(filename)
    return ct


def read_spect(filename, input_unit=None):
    spect = ImageSPECT()
    spect.read(filename)
    if spect.unit is None and input_unit is None:
        fatal(f"Error: no image unit is specified while reading"
              f" {filename} (considered as SPECT)")
    if input_unit is not None:
        spect.unit = input_unit
    else:
        if spect.unit is None:
            fatal(f"Error: no image unit is specified while reading"
                  f" {filename} (considered as SPECT)")
    return spect


def read_roi(filename, name, effective_time_h=None):
    roi = ImageROI(name)
    roi.read(filename)
    if effective_time_h is not None:
        roi.effective_time_h = effective_time_h
    return roi


def read_dose(filename, input_unit=None):
    d = ImageDose()
    d.read(filename)
    if d.unit is None:
        # set Gy by default
        if input_unit is None:
            d.unit = 'Gy'
        else:
            d.unit = input_unit
    else:
        if d.image_type is not None:
            if d.unit != input_unit:
                fatal(f"Image metadata have {d.unit} as pixel unit, "
                      f"but input unit is {input_unit}, error.")
    return d


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


class ImageBase(rmd.ClassWithMetaData):
    authorized_units = []
    unit_default_values = {}
    image_type = None

    # the metadata members are attributes that will be
    # stored/loaded on disk (in json file)
    _metadata_fields = {'image_type': str,
                        'description': str,
                        'filename': str,
                        'acquisition_datetime': str,
                        'unit': str}

    def __init__(self):
        super().__init__()
        self.image = None
        # metadata infos
        self.description = ""
        self.acquisition_datetime = None
        # internal parameters
        self._image_filename = None
        self._image_path = None
        self._image_header = None
        self._unit = None
        self._unit_default_value = 0
        # unit converter
        self.unit_converter = {}

    @property
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, value):
        """
        Only change the unit when it is not known (equal to None).
        Otherwise, user "convert"
        """
        if self._unit == value:
            return
        if self.image_type is None:
            fatal("Cannot set the unit, the image type is not known "
                  f"(use change_image_type function, with one "
                  f"of {[k for k in image_builders]})")
        if len(self.authorized_units) < 1 and value not in self.authorized_units:
            fatal(f"Unauthorized unit {value}. Must be one of {self.authorized_units}")
        if self._unit is not None:
            fatal(
                f"Cannot set the unit to {value} (current value is {self._unit}) ; Use convert functions or delete metadata")
        self._unit = value
        if value in self.unit_default_values:
            self._unit_default_value = self.unit_default_values[value]

    @property
    def image_path(self):
        return self._image_path

    @image_path.setter
    def image_path(self, value):
        self._image_path = os.path.abspath(value)
        self._image_filename = os.path.basename(value)

    @property
    def filename(self):
        return self._image_filename

    @filename.setter
    def filename(self, value):
        self._image_filename = os.path.basename(value)
        self._image_path = os.path.abspath(value)

    def require_unit(self, unit):
        if unit != self.unit:
            fatal(f"The unit '{unit}' is required while it is {self.unit}")

    def convert_to_unit(self, new_unit):
        if new_unit not in self.unit_converter:
            fatal(f"I dont know how to convert to '{new_unit}'")
        # get the function's name
        f = self.unit_converter[new_unit]
        # and call it (probably there is a better way)
        getattr(self, f)()

    @property
    def voxel_volume_cc(self):
        if self.image is not None:
            v = np.prod(self.image.GetSpacing()) / 1000
            return v
        else:
            return 0

    @property
    def unit_default_value(self):
        return self._unit_default_value

    def read(self, filepath):
        self.image_path = filepath
        if not os.path.exists(filepath):
            fatal(f'Image: the filename {filepath} does not exist.')
        self.image = sitk.ReadImage(filepath)
        self.read_metadata()

    def write(self, filepath=None):
        if filepath is None:
            filepath = self.image_path
            if filepath is not None:
                fatal(f'Provide the filepath to write the image to.')
        self.image_path = filepath
        if self.image is not None:
            sitk.WriteImage(self.image, filepath)
        self.write_metadata()

    def read_metadata(self):
        json_filename = self.get_metadata_filepath()
        current_image_type = self.image_type
        p = self.image_path
        if os.path.exists(json_filename):
            self.load_from_json(json_filename)
        # put back image path and check image filename
        read_filename = self._image_filename
        self.image_path = p
        if self._image_filename != read_filename:
            fatal(f'Error: the filename in the sidecar json is "{read_filename}" '
                  f'while we expected "{self.filename}"')
        if self.image_type != current_image_type:
            fatal(f'Image type is "{current_image_type}" but reading '
                  f'metadata "{self.image_type}" in the file {json_filename}')

    def read_image_header(self):
        reader = sitk.ImageFileReader()
        reader.SetFileName(str(self.image_path))
        reader.LoadPrivateTagsOn()
        reader.ReadImageInformation()
        self._image_header = Box()
        self._image_header.size = reader.GetSize()
        self._image_header.spacing = reader.GetSpacing()
        self._image_header.origin = reader.GetOrigin()
        self._image_header.pixel_type = sitk.GetPixelIDValueAsString(reader.GetPixelID())

    def write_metadata(self):
        json_filename = self.get_metadata_filepath()
        self.save_to_json(json_filename)

    def get_metadata_filepath(self):
        if self.image_path is not None:
            return str(self.image_path) + '.json'
        return None

    def info(self):
        json_filename = self.get_metadata_filepath()
        js = f'(metadata: {self.get_metadata_filepath()})'
        if json_filename is not None and not os.path.exists(json_filename):
            js = '(no metadata available)'
        s = f'Image:   {self._image_filename} {js}\n'
        s += f'Type:    {self.image_type}\n'
        s += f'Loaded:  {self.image is not None}\n'
        s += f'Unit:    {self.unit}\n'
        s += f'Date:    {self.acquisition_datetime}\n'
        if self.image is not None:
            s += f'Size:    {self.image.GetSize()}\n'
            s += f'Spacing: {self.image.GetSpacing()}\n'
            s += f'Origin:  {self.image.GetOrigin()}\n'
            s += f'Pixel :  {sitk.GetPixelIDValueAsString(self.image.GetPixelID())}'
        else:
            if self._image_header is not None:
                s += f'Size:    {self._image_header.size}\n'
                s += f'Spacing: {self._image_header.spacing}\n'
                s += f'Origin:  {self._image_header.origin}\n'
                s += f'Pixel:   {self._image_header.pixel_type}'
        return s


class ImageCT(ImageBase):
    authorized_units = ['HU', 'g/cm3']  # FIXME add attenuation
    unit_default_values = {'HU': -1000, 'g/cm3': 0}
    image_type = "CT"

    def __init__(self):
        super().__init__()
        self.unit = 'HU'

    def compute_densities(self):  # FIXME to remove ?
        if self.unit != 'HU':
            fatal(f'Unit {self.unit} is not HU, cannot compute density CT')
        density_ct = copy.copy(self)
        density_ct._unit = 'g/cm3'
        # Simple conversion from HU to g/cm^3
        density_ct.image = self.image / 1000 + 1
        # the density of air is near 0, not negative
        a = sitk.GetArrayFromImage(density_ct.image)
        a[a < 0] = 0
        density_ct.image = sitk.GetImageFromArray(a)
        density_ct.image.CopyInformation(self.image)
        return density_ct


class ImageSPECT(ImageBase):
    authorized_units = ['Bq', 'Bq/mL', "SUV"]
    unit_default_values = {'Bq': 0, 'Bq/mL': 0, "SUV": 0}
    image_type = "SPECT"

    _metadata_fields = {
        **ImageBase._metadata_fields,  # Inherit base class fields
        'injection_datetime': str,
        'injection_activity_mbq': float,
        'body_weight_kg': float
    }

    def __init__(self):
        super().__init__()
        self._unit = None
        # metadata
        self.injection_datetime = None
        self.injection_activity_mbq = None
        self.body_weight_kg = None
        # unit converter
        self.unit_converter = {
            'Bq': "convert_to_bq",
            'Bq/mL': "convert_to_bqml",
            'SUV': "convert_to_suv",
        }

    def info(self):
        s = super().info() + '\n'
        s += f'Body weight:    {self.body_weight_kg} kq\n'
        s += f'Injection date: {self.injection_datetime}\n'
        s += f'Injection:      {self.injection_activity_mbq} MBq\n'
        if self.image is not None:
            s += f'Total activity: {self.compute_total_activity()} MBq\n'
        return s

    def convert_to_bq(self):
        if self.unit == 'Bq/mL':
            self.image = self.image * self.voxel_volume_cc
            self._unit = 'Bq'
        if self.unit == "SUV":
            arr = sitk.GetArrayFromImage(self.image)
            arr = arr * self.voxel_volume_cc * (self.injection_activity_mbq * self.body_weight_kg)
            im = sitk.GetImageFromArray(arr)
            im.CopyInformation(self.image)
            self.image = im
            self._unit = 'Bq'

    def convert_to_bqml(self):
        if self.unit == 'Bq':
            self.image = self.image / self.voxel_volume_cc
            self._unit = "Bq/mL"
        if self.unit == "SUV":
            self.convert_to_bq()
            self.convert_to_bqml()

    def convert_to_suv(self):
        if self.body_weight_kg is None:
            fatal(f'To convert to SUV, body_weight_kg cannot be None (SPECT image {self._image_filename})')
        if self.injection_activity_mbq is None:
            fatal(f'To convert to SUV, injection_activity_MBq cannot be None (SPECT image {self._image_filename})')
        arr = sitk.GetArrayFromImage(self.image)
        # convert to Bq/mL first
        self.convert_to_bqml()
        # convert to SUV
        arr = arr / (self.injection_activity_mbq * self.body_weight_kg)
        im = sitk.GetImageFromArray(arr)
        im.CopyInformation(self.image)
        self.image = im
        self._unit = 'SUV'

    def compute_total_activity(self):
        if self.unit is None:
            return -1
        if self.image is None:
            fatal("Image data not loaded.")
        if self.unit == 'Bq':
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
        return get_time_from_injection_h(self.injection_datetime, self.acquisition_datetime)

    @time_from_injection_h.setter
    def time_from_injection_h(self, value):
        if self.injection_datetime is None and self.acquisition_datetime is None:
            self.injection_datetime = "1970-01-01 00:00:00"
            d = datetime.datetime.strptime(self.injection_datetime, "%Y-%m-%d %H:%M:%S")
            self.acquisition_datetime = (d + datetime.timedelta(hours=value)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            fatal(f'Cannot set the time from injection since injection_datetime or acquisition_datetime exists')


class ImageROI(ImageBase):
    authorized_units = ['label']
    unit_default_values = {'label': 0}
    image_type = "ROI"

    _metadata_fields = {
        **ImageBase._metadata_fields,  # Inherit base class fields
        'name': str,
        'effective_time_h': float
    }

    def __init__(self, name):
        super().__init__()
        self.name = name
        self._unit = 'label'
        self.effective_time_h = None
        self.mass_g = None
        self.volume_cc = None

    def info(self):
        s = super().info() + '\n'
        s += f'Teff:   {self.effective_time_h} h\n'
        s += f'Mass:   {self.mass_g} g\n'
        s += f'Volume: {self.volume_cc} cc'
        return s

    def update_mass_and_volume(self, density_ct):
        # compute mass
        a = sitk.GetArrayViewFromImage(self.image)
        da = sitk.GetArrayViewFromImage(density_ct.image)
        d = da[a == 1]
        self.mass_g = np.sum(d) * self.voxel_volume_cc
        self.volume_cc = len(d) * self.voxel_volume_cc


class ImageDose(ImageBase):
    authorized_units = ['Gy', 'Gy/s']
    unit_default_values = {'Gy': 0, 'Gy/s': 0}
    image_type = "Dose"

    def __init__(self):
        super().__init__()
        self._unit = None


image_builders = {
    "CT": ImageCT,
    "SPECT": ImageSPECT,
    "ROI": ImageROI,
    "Dose": ImageDose}


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
        raise click.BadParameter('Spacing must be either one or three values')


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


def OLD_resample_ct_like_spect(spect, ct, verbose=True):
    if not images_have_same_domain(spect, ct):
        sigma = [0.5 * sp for sp in ct.GetSpacing()]
        if verbose:
            print(
                f"Resample ct image ({ct.GetSize()}) to spacing={spect.GetSpacing()} size={spect.GetSize()}"
            )
        ct = apply_itk_gauss_smoothing(ct, sigma)
        ct = resample_itk_image_like(ct, spect, -1000, linear=True)
    ct_a = sitk.GetArrayFromImage(ct)
    return ct_a


def apply_itk_gauss_smoothing(img, sigma):
    if sigma is None:
        return img
    if sigma == "auto" or sigma == 0:
        sigma = [0.5 * sp for sp in img.GetSpacing()]
    gauss_filter = sitk.SmoothingRecursiveGaussianImageFilter()
    gauss_filter.SetSigma(sigma)
    gauss_filter.SetNormalizeAcrossScale(True)
    return gauss_filter.Execute(img)


def resample_ct_like(ct: ImageCT, like: ImageBase, gaussian_sigma=None):
    if images_have_same_domain(ct.image, like.image):
        return ct
    o = copy.copy(ct)
    o.image = apply_itk_gauss_smoothing(ct.image, gaussian_sigma)
    o.image = resample_itk_image_like(o.image, like.image, o.unit_default_value, linear=True)
    return o


def resample_dose_like(ct: ImageDose, like: ImageBase, gaussian_sigma=None):
    if images_have_same_domain(ct.image, like.image):
        return ct
    o = copy.copy(ct)
    o.image = apply_itk_gauss_smoothing(ct.image, gaussian_sigma)
    o.image = resample_itk_image_like(o.image, like.image, o.unit_default_value, linear=True)
    return o


def resample_ct_spacing(ct: ImageCT, spacing, gaussian_sigma=None):
    if image_has_this_spacing(ct.image, spacing):
        return
    o = copy.copy(ct)
    o.image = apply_itk_gauss_smoothing(ct.image, gaussian_sigma)
    o.image = resample_itk_image_spacing(o.image, spacing, o.unit_default_value, linear=True)
    return o


def resample_spect_like(spect: ImageSPECT, like: ImageBase, gaussian_sigma=None):
    if images_have_same_domain(spect.image, like.image):
        return spect
    o = copy.copy(spect)
    o.image = apply_itk_gauss_smoothing(spect.image, gaussian_sigma)
    # convert to bqml and back to initial unit
    initial_unit = o.unit
    o.convert_to_bqml()
    o.image = resample_itk_image_like(o.image, like.image, o.unit_default_value, linear=True)
    o.convert_to_unit(initial_unit)
    return o


def resample_spect_spacing(spect: ImageSPECT, spacing, gaussian_sigma=None):
    if image_has_this_spacing(spect.image, spacing):
        return
    o = copy.copy(spect)
    o.image = apply_itk_gauss_smoothing(spect.image, gaussian_sigma)
    # convert to bqml and back to initial unit
    initial_unit = o.unit
    o.convert_to_bqml()
    o.image = resample_itk_image_spacing(o.image, spacing, o.unit_default_value, linear=True)
    o.convert_to_unit(initial_unit)
    # take the volume into account if needed
    return o


def resample_roi_like(roi: ImageROI, like: ImageBase):
    if images_have_same_domain(roi.image, like.image):
        return roi
    o = copy.copy(roi)
    o.image = resample_itk_image_like(roi.image, like.image, o.unit_default_value, linear=False)
    return o


def resample_roi_spacing(roi: ImageROI, spacing):
    if image_has_this_spacing(roi.image, spacing):
        return
    o = copy.copy(roi)
    o.image = resample_itk_image_spacing(o.image, spacing, o.unit_default_value, linear=False)
    return o


def OLD_resample_roi_like_spect(spect, roi, convert_to_np=True, verbose=True):
    if not images_have_same_domain(spect, roi):
        if verbose:
            print(
                f"Resample roi mask ({roi.GetSize()}) to spacing={spect.GetSpacing()} size={spect.GetSize()}"
            )
        roi = resample_itk_image_like(roi, spect, 0, linear=False)
    if convert_to_np:
        roi = sitk.GetArrayFromImage(roi)
    return roi


def get_stats_in_rois(spect, ct, rois_list):
    # load spect
    spect = sitk.ReadImage(spect)
    volume_voxel_cc = np.prod(spect.GetSpacing()) / 1000
    spect_a = sitk.GetArrayFromImage(spect)
    # load ct
    ct = sitk.ReadImage(ct)
    ct_a = OLD_resample_ct_like_spect(spect, ct, verbose=False)
    densities = convert_ct_to_densities(ct_a)
    # prepare key
    res = {}
    # loop on rois
    for roi in rois_list:
        # read roi mask and resample like spect
        r = sitk.ReadImage(roi.roi_filename)
        roi_a = OLD_resample_roi_like_spect(spect, r, verbose=False)
        # compute stats
        s = image_roi_stats_OLD(spect_a, roi_a)
        # compute mass
        d = densities[roi_a == 1]
        mass = np.sum(d) * volume_voxel_cc
        s["mass_g"] = mass
        # set in the db
        res[roi.roi_name] = s
    return res


def image_roi_stats_OLD(spect_a, roi_a):
    # select pixels
    p = spect_a[roi_a == 1]
    # compute stats
    return {
        "mean": float(np.mean(p)),
        "std": float(np.std(p)),
        "min": float(np.min(p)),
        "max": float(np.max(p)),
        "sum": float(np.sum(p)),
    }


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
        print(f'Total image1 = {np.sum(img1)}')
        print(f'Total image2 = {np.sum(img2)}')
    return ok


def dilate_mask(img, dilatation_mm):
    # convert radius in vox
    radius = [int(round(dilatation_mm / img.GetSpacing()[0])),
              int(round(dilatation_mm / img.GetSpacing()[1])),
              int(round(dilatation_mm / img.GetSpacing()[2]))]
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
    m = {'spect': spect, 'roi': roi}
    if ct is not None:
        m['ct'] = ct
    if resample_like not in m:
        fatal(f"the option resample_like, must be {m}, while it is {resample_like}")
    resample_like = m[resample_like]
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
        "volume_cc": float(len(p) * roi.voxel_volume_cc)
    }

    # for ct (densities)
    if ct is not None:
        ct = resample_ct_like(ct, resample_like)
        densities = ct.compute_densities()
        roi.update_mass_and_volume(densities)
        res["mass_g"] = roi.mass_g

    return res


def mhd_find_raw_file(mhd_file_path):
    with open(mhd_file_path, 'r') as mhd_file:
        for line in mhd_file:
            if line.startswith('ElementDataFile'):
                return line.split('=')[1].strip()


def mhd_replace_raw(mhd_file_path, new_raw_filename):
    new_raw_filename = new_raw_filename.replace('.gz', '')
    with open(mhd_file_path, 'r') as file:
        lines = file.readlines()
    with open(mhd_file_path, 'w') as file:
        for line in lines:
            if line.startswith('ElementDataFile'):
                file.write(f'ElementDataFile = {new_raw_filename}\n')
            else:
                file.write(line)


def is_mhd_file(filepath):
    _, extension = os.path.splitext(filepath)
    return extension.lower() == '.mhd'


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
        raw_path = Path(str(raw_path) + '.gz')
        new_raw_path = Path(str(new_raw_path) + '.gz')
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
    print(f"Copy {mhd_path} + {os.path.basename(raw_path)} "
          f"--->   {new_mhd_path} + {os.path.basename(new_raw_path)}")


def copy_or_move_image(source_path, dest_path, mode):
    modes = ['move', 'copy', 'dry_run', 'print_only']
    if mode not in modes:
        fatal(f'Unknown mode {mode}, available modes: {", ".join(modes)}')
    if is_mhd_file(source_path):
        return mhd_copy_or_move(source_path, dest_path, mode)
    if mode == 'copy':
        shutil.copy(source_path, dest_path)
        return
    if mode == "move":
        shutil.move(source_path, dest_path)
        return
    print(f"Copy {source_path}  --->   {dest_path}")


def get_time_from_injection_h(injection_datetime, acquisition_datetime):
    i_date = None
    a_date = None
    try:
        i_date = datetime.datetime.strptime(injection_datetime, "%Y-%m-%d %H:%M:%S")
    except Exception:
        fatal(f'Cannot get the time from injection since injection_datetime '
              f'is {injection_datetime} and cannot be interpreted')
    try:
        a_date = datetime.datetime.strptime(acquisition_datetime, "%Y-%m-%d %H:%M:%S")
    except Exception:
        fatal(f'Cannot get the time from injection since acquisition_datetime '
              f'is {acquisition_datetime} and cannot be interpreted')
    hours_diff = (a_date - i_date).total_seconds() / 3600
    return hours_diff
