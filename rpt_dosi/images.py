import SimpleITK as sitk
import math
from .helpers import fatal
import numpy as np
import os
import click
import copy
import json
from box import BoxList


def read_ct(filename):
    ct = ImageCT()
    ct.read(filename)
    return ct


def read_spect(filename, unit):
    spect = ImageSPECT()
    spect.read(filename)
    spect.unit = unit
    return spect


def read_roi(filename, name, effective_time_h=None):
    roi = ImageROI(name)
    roi.read(filename)
    roi.effective_time_h = effective_time_h
    return roi


def read_dose(filename, unit):
    d = ImageDose(unit)
    d.read(filename)
    return d


def read_list_of_rois(filename):
    rois = []
    with open(filename, "r") as f:
        rois_file = BoxList(json.load(f))
        for roi in rois_file:
            Teff = None
            if "time_eff_h" in roi:
                Teff = roi["time_eff_h"]
            r = read_roi(roi.roi_filename, roi.roi_name, Teff)
            rois.append(r)
    return rois


class ImageBase:
    authorized_units = []
    default_values = {}

    def __init__(self, name=None):
        self.name = name
        self.image = None
        self.filename = None
        self.dicom_folder = None
        self.dicom_filename = None
        self.acquisition_datetime = None
        # internal parameters
        self._unit = None
        self._default_value = 0

    @property
    def unit(self):
        return self._unit

    @property
    def voxel_volume_ml(self):
        v = np.prod(self.image.GetSpacing()) / 1000
        return v

    @property
    def default_value(self):
        return self._default_value

    @unit.setter
    def unit(self, value):
        if value not in self.authorized_units:
            raise ValueError(f"Unauthorized unit {value}. Must be one of {self.authorized_units}")
        if value not in self.default_values:
            raise ValueError(f'Undefined default value for unit {value}. Must be one of {self.default_values}')
        self._unit = value
        self._default_value = self.default_values[value]

    def read(self, filename):
        self.filename = filename
        self.image = sitk.ReadImage(filename)
        if self.name is None:
            self.name = os.path.basename(self.filename)

    def read_dicom(self, filename):
        if os.path.isdir(filename):
            self.dicom_folder = filename
            # FIXME open + unit ?
        if os.path.isfile(filename):
            self.dicom_filename = filename
            # FIXME open + unit ?
        # FIXME error detection

    def __str__(self):
        return f"Image: {self.name} unit={self.unit}"


class ImageCT(ImageBase):
    authorized_units = ['HU', 'gcm3']  # FIXME add attenuation
    default_values = {'HU': -1000, 'gcm3': 0}

    def __init__(self):
        super().__init__()
        self.unit = 'HU'

    def read(self, filename):
        super().read(filename)
        self.unit = 'HU'

    def __str__(self):
        return f"CT: {self.name} unit={self.unit}, vox_vol={self.voxel_volume_ml} ml"

    def get_densities(self):
        if self.unit != 'HU':
            raise ValueError(f'Unit {self.unit} is not HU, cannot compute density CT')
        density_ct = copy.copy(self)
        density_ct.unit = 'gcm3'
        # Simple conversion from HU to g/cm^3
        density_ct.image = self.image / 1000 + 1
        # the density of air is near 0, not negative
        a = sitk.GetArrayFromImage(density_ct.image)
        a[a < 0] = 0
        density_ct.image = sitk.GetImageFromArray(a)
        density_ct.image.CopyInformation(self.image)
        return density_ct


class ImageSPECT(ImageBase):
    authorized_units = ['Bq', 'BqmL', "SUV"]
    default_values = {'Bq': 0, 'BqmL': 0, "SUV": 0}

    def __init__(self):
        super().__init__()
        self.injection_datetime = None
        self.injection_activity_mbq = None
        self.time_from_injection_h = None
        self.body_weight_kg = None
        self.converter = {"Bq": self._convert_to_bq}

    def __str__(self):
        return (f"SPECT: {self.name} unit={self.unit}, "
                f"vox_vol={self.voxel_volume_ml} ml, "
                f"body_weight={self.body_weight_kg}, "
                f"injection_datetime={self.injection_datetime}, "
                f"injection_activity_mbq={self.injection_activity_mbq}")

    @ImageBase.unit.setter
    def unit(self, value):
        if value == "Bqml":
            self._convert_to_bqml()
        if value == "Bq":
            self._convert_to_bq()
        if value == "SUV":
            self._convert_to_suv()
        super(ImageSPECT, self.__class__).unit.fset(self, value)

    def _convert_to_bq(self):
        if self.unit == 'BqmL':
            self.image = self.image * self.voxel_volume_ml
        if self.unit == "SUV":
            arr = sitk.GetArrayFromImage(self.image)
            arr = arr * self.voxel_volume_ml * (self.injection_activity_mbq * self.body_weight_kg)
            im = sitk.GetImageFromArray(arr)
            im.CopyInformation(self.image)
            self.image = im

    def _convert_to_bqml(self):
        if self.unit == 'Bq':
            self.image = self.image / self.voxel_volume_ml
        if self.unit == "SUV":
            self.unit = "Bq"
            self.unit = "BqmL"

    def _convert_to_suv(self):
        if self.body_weight_kg is None:
            raise ValueError(f'To convert to SUV, body_weight_kg cannot be None (SPECT image {self.filename})')
        if self.injection_activity_mbq is None:
            raise ValueError(f'To convert to SUV, injection_activity_MBq cannot be None (SPECT image {self.filename})')
        arr = sitk.GetArrayFromImage(self.image)
        # convert to bqml first
        self.unit = "BqmL"
        # convert to SUV
        arr = arr / self.voxel_volume_ml / (self.injection_activity_mbq * self.body_weight_kg)
        im = sitk.GetImageFromArray(arr)
        im.CopyInformation(self.image)
        self.image = im

    def compute_total_activity(self):
        if self.image is None:
            raise ValueError("Image data not loaded.")
        arr = sitk.GetArrayViewFromImage(self.image)
        total_activity = np.sum(arr)
        if self.unit == 'BqmL':
            total_activity = total_activity * self.voxel_volume_ml
        return total_activity


class ImageROI(ImageBase):
    authorized_units = ['label']
    default_values = {'label': 0}

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.unit = 'label'
        self.effective_time_h = None
        self.mass_g = None
        self.volume_ml = None

    def __str__(self):
        s = f"ROI: {self.name} unit={self.unit}, vox_vol={self.voxel_volume_ml} ml"
        s += f", Teff = {self.effective_time_h} h"
        if self.mass_g is not None:
            s += f", mass={self.mass_g} g"
        if self.volume_ml is not None:
            s += f", volume={self.volume_ml} ml"
        return s

    def update_mass_and_volume(self, density_ct):
        # compute mass
        a = sitk.GetArrayViewFromImage(self.image)
        da = sitk.GetArrayViewFromImage(density_ct.image)
        d = da[a == 1]
        self.mass_g = np.sum(d) * self.voxel_volume_ml
        self.volume_ml = len(d) * self.voxel_volume_ml


class ImageDose(ImageBase):
    authorized_units = ['Gy', 'Gy_sec']
    default_values = {'Gy': 0, 'Gy_sec': 0}

    def __init__(self, unit):
        super().__init__()
        self.unit = unit

    def __str__(self):
        s = f"Dose: {self.name} unit={self.unit}, vox_vol={self.voxel_volume_ml} ml"
        return s


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


def image_have_same_spacing(image1, spacing, tolerance=1e-5):
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
    o.image = resample_itk_image_like(o.image, like.image, o.default_value, linear=True)
    return o


def resample_dose_like(ct: ImageDose, like: ImageBase, gaussian_sigma=None):
    if images_have_same_domain(ct.image, like.image):
        return ct
    o = copy.copy(ct)
    o.image = apply_itk_gauss_smoothing(ct.image, gaussian_sigma)
    o.image = resample_itk_image_like(o.image, like.image, o.default_value, linear=True)
    return o


def resample_ct_spacing(ct: ImageCT, spacing: list[float], gaussian_sigma=None):
    if image_have_same_spacing(ct.image, spacing):
        return
    o = copy.copy(ct)
    o.image = apply_itk_gauss_smoothing(ct.image, gaussian_sigma)
    o.image = resample_itk_image_spacing(o.image, spacing, o.default_value, linear=True)
    return o


def resample_spect_like(spect: ImageSPECT, like: ImageBase, gaussian_sigma=None):
    if images_have_same_domain(spect.image, like.image):
        return spect
    o = copy.copy(spect)
    o.image = apply_itk_gauss_smoothing(spect.image, gaussian_sigma)
    o.image = resample_itk_image_like(o.image, like.image, o.default_value, linear=True)
    # take the volume into account if needed
    if o.unit == 'Bq' or o.unit == 'counts':
        scaling = spect.voxel_volume_ml / like.voxel_volume_ml
        o.image = o.image * scaling
    print(o.image)
    return o


def resample_spect_spacing(spect: ImageSPECT, spacing: list[float], gaussian_sigma=None):
    if image_have_same_spacing(spect.image, spacing):
        return
    o = copy.copy(spect)
    o.image = apply_itk_gauss_smoothing(spect.image, gaussian_sigma)
    o.image = resample_itk_image_spacing(o.image, spacing, o.default_value, linear=True)
    # take the volume into account if needed
    if o.unit == 'Bq' or o.unit == 'counts':
        v = np.prod(spacing) / 1000
        scaling = v / spect.voxel_volume_ml
        o.image = o.image * scaling
    return o


def resample_roi_like(roi: ImageROI, like: ImageBase):
    if images_have_same_domain(roi.image, like.image):
        return roi
    o = copy.copy(roi)
    o.image = resample_itk_image_like(roi.image, like.image, o.default_value, linear=False)
    return o


def resample_roi_spacing(roi: ImageROI, spacing: list[float]):
    if image_have_same_spacing(roi.image, spacing):
        return
    o = copy.copy(roi)
    o.image = resample_itk_image_spacing(o.image, spacing, o.default_value, linear=False)
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
    volume_voxel_mL = np.prod(spect.GetSpacing()) / 1000
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
        s = image_roi_stats(spect_a, roi_a)
        # compute mass
        d = densities[roi_a == 1]
        mass = np.sum(d) * volume_voxel_mL
        s["mass_g"] = mass
        # set in the db
        res[roi.roi_name] = s
    return res


def image_roi_stats(spect_a, roi_a):
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
    print(f'Total image1 = {np.sum(img1)}')
    print(f'Total image2 = {np.sum(img2)}')
    ok = np.allclose(img1, img2, atol=tol)
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
