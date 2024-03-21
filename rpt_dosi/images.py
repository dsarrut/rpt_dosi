import SimpleITK as sitk
import math
from .helpers import fatal
import numpy as np
import os
import click
import copy
import json
from box import BoxList


def read_image(filename):
    im = ImageBase()
    im.filename = filename
    im.read_metadata()
    if im.image_type is not None:
        im = build_image_from_type(im.image_type)
    im.read(filename)
    return im


def change_image_type(image, image_type):
    output = build_image_from_type(image_type)
    output.image = image.image
    return output


def build_image_from_type(image_type):
    if image_type not in image_builders:
        raise ValueError(f"This image type '{image_type}' is not known. "
                         f"Known image types: {image_builders.keys()}")
    the_class = image_builders[image_type]
    output = the_class()
    return output


def read_ct(filename):
    ct = ImageCT()
    ct.read(filename)
    return ct


def read_spect(filename):
    spect = ImageSPECT()
    spect.read(filename)
    return spect


def read_roi(filename, name, effective_time_h=None):
    roi = ImageROI(name)
    roi.read(filename)
    roi.effective_time_h = effective_time_h
    return roi


def read_dose(filename):
    d = ImageDose()
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
    image_type = None

    def __init__(self):
        self.image = None
        self.description = ""
        self.filename = None
        self.dicom_folder = None  # FIXME later
        self.dicom_filename = None  # FIXME later
        self.acquisition_datetime = None
        # internal parameters
        self._unit = None
        self._default_value = 0

    @property
    def unit(self):
        return self._unit

    @property
    def voxel_volume_ml(self):
        if self.image is not None:
            v = np.prod(self.image.GetSpacing()) / 1000
            return v
        else:
            return 0

    @property
    def default_value(self):
        return self._default_value

    @unit.setter
    def unit(self, value):
        if self.image_type is None:
            raise ValueError("Cannot set the unit, the image type is not known "
                             f"(use change_image_type function, with one "
                             f"of {[k for k in image_builders]})")
        if value not in self.authorized_units:
            raise ValueError(f"Unauthorized unit {value}. Must be one of {self.authorized_units}")
        if value not in self.default_values:
            raise ValueError(f'Undefined default value for unit {value}. Must be one of {self.default_values}')
        self._unit = value
        self._default_value = self.default_values[value]

    def require_unit(self, unit):
        if unit != self.unit:
            raise ValueError(f"The unit '{unit}' is required while it is {self.unit}")

    def read(self, filename):
        self.filename = filename
        self.image = sitk.ReadImage(filename)
        self.read_metadata()

    def write(self, filename):
        sitk.WriteImage(self.image, filename)
        self.filename = filename
        self.write_metadata()

    def read_metadata(self):
        json_filename = self._get_json_filename()
        if os.path.exists(json_filename):
            with open(json_filename, 'r') as json_file:
                metadata = json.load(json_file)
                self._apply_metadata(metadata)

    def write_metadata(self):
        metadata = self._gather_metadata()
        json_filename = self._get_json_filename()
        with open(json_filename, 'w') as json_file:
            json.dump(metadata, json_file, indent=2)

    def _get_json_filename(self):
        if self.filename:
            base_filename = self.filename
            # Keep removing extensions until there are none left
            while os.path.splitext(base_filename)[1] != '':
                base_filename = os.path.splitext(base_filename)[0]
            return base_filename + '.json'
        return None

    def _apply_metadata(self, metadata):
        if 'image_type' in metadata:
            if (self.image_type is not None and
                    self.image_type != metadata['image_type']):
                raise ValueError(f'This expected image type is {self.image_type} '
                                 f'but the metadata has type {metadata["image_type"]}')
            self.image_type = metadata['image_type']
        if 'description' in metadata:
            self.description = metadata['description']
        if 'unit' in metadata:
            self._unit = metadata['unit']
        if 'acquisition_datetime' in metadata:
            self.acquisition_datetime = metadata['acquisition_datetime']

    def _gather_metadata(self):
        metadata = {
            'filename': str(self.filename),
            'image_type': self.image_type,
            'description': self.description,
            'unit': self.unit,
            'acquisition_datetime': str(self.acquisition_datetime)
        }
        return metadata

    def read_dicom(self, filename):
        if os.path.isdir(filename):
            self.dicom_folder = filename
            # FIXME open + unit ?
        if os.path.isfile(filename):
            self.dicom_filename = filename
            # FIXME open + unit ?
        # FIXME error detection
        fatal(f'Not yet implemented')

    def info(self):
        json_filename = self._get_json_filename()
        js = f'(metadata: {self._get_json_filename()})'
        if not os.path.exists(json_filename):
            js = '(no metadata available)'
        s = f'Image:  {self.filename} {js}\n'
        s += f'Type:   {self.image_type}\n'
        s += f'Loaded: {self.image is not None}\n'
        if self.image is not None:
            s += f'Size:    {self.image.GetSize()}\n'
            s += f'Spacing: {self.image.GetSpacing()}\n'
            s += f'Origin:  {self.image.GetOrigin()}\n'
        s += f'Unit:   {self.unit}\n'
        s += f'Date:   {self.acquisition_datetime}\n'
        return s

    def __str__(self):
        return f"Image: unit={self.unit}"


class ImageCT(ImageBase):
    authorized_units = ['HU', 'g/cm3']  # FIXME add attenuation
    default_values = {'HU': -1000, 'g/cm3': 0}
    image_type = "CT"

    def __init__(self):
        super().__init__()
        self.unit = 'HU'

    def __str__(self):
        return f"CT: unit={self.unit}"

    def compute_densities(self):
        if self.unit != 'HU':
            raise ValueError(f'Unit {self.unit} is not HU, cannot compute density CT')
        density_ct = copy.copy(self)
        density_ct.unit = 'g/cm3'
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
    default_values = {'Bq': 0, 'Bq/mL': 0, "SUV": 0}
    image_type = "SPECT"

    def __init__(self):
        super().__init__()
        self.unit = 'Bq'
        self.injection_datetime = None
        self.injection_activity_mbq = None
        self.time_from_injection_h = None
        self.body_weight_kg = None
        self.converter = {"Bq": self.convert_to_bq}

    def __str__(self):
        return (f"SPECT: unit={self.unit}, "
                f"body_weight={self.body_weight_kg}, "
                f"injection_datetime={self.injection_datetime}, "
                f"injection_activity_mbq={self.injection_activity_mbq}")

    def info(self):
        s = super().info() + '\n'
        s += f'Body weight:    {self.body_weight_kg} kq\n'
        s += f'Injection date: {self.injection_datetime}\n'
        s += f'Injection:      {self.injection_activity_mbq} MBq\n'
        s += f'Total activity: {self.compute_total_activity()} MBq\n'
        return s

    def _apply_metadata(self, metadata):
        super()._apply_metadata(metadata)
        if 'body_weight_kg' in metadata:
            self.body_weight_kg = metadata['body_weight_kg']
        if 'injection_activity_mbq' in metadata:
            self.injection_activity_mbq = metadata['injection_activity_mbq']
        if 'injection_datetime' in metadata:
            self.injection_datetime = metadata['injection_datetime']

    def _gather_metadata(self):
        metadata = super()._gather_metadata()
        m = {
            'body_weight_kg': self.body_weight_kg,
            'injection_activity_mbq': self.injection_activity_mbq,
            'injection_datetime': self.injection_datetime
        }
        metadata.update(m)
        return metadata

    @ImageBase.unit.setter
    def unit(self, value):
        if value == "Bq/mL":
            self.convert_to_bqml()
        if value == "Bq":
            self.convert_to_bq()
        if value == "SUV":
            self.convert_to_suv()
        # set the unit
        self._unit = value

    def convert_to_bq(self):
        if self.unit == 'Bq/mL':
            self.image = self.image * self.voxel_volume_ml
        if self.unit == "SUV":
            arr = sitk.GetArrayFromImage(self.image)
            arr = arr * self.voxel_volume_ml * (self.injection_activity_mbq * self.body_weight_kg)
            im = sitk.GetImageFromArray(arr)
            im.CopyInformation(self.image)
            self.image = im

    def convert_to_bqml(self):
        if self.unit == 'Bq':
            self.image = self.image / self.voxel_volume_ml
            self._unit = "Bq/mL"
        if self.unit == "SUV":
            self.unit = "Bq"  # convert SUV to Bq
            self.unit = "Bq/mL"  # convert Bq to BqmL

    def convert_to_suv(self):
        if self.body_weight_kg is None:
            raise ValueError(f'To convert to SUV, body_weight_kg cannot be None (SPECT image {self.filename})')
        if self.injection_activity_mbq is None:
            raise ValueError(f'To convert to SUV, injection_activity_MBq cannot be None (SPECT image {self.filename})')
        arr = sitk.GetArrayFromImage(self.image)
        # convert to Bq/mL first
        self.unit = "Bq/mL"
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
        if self.unit == 'Bq/mL':
            total_activity = total_activity * self.voxel_volume_ml
        return total_activity


class ImageROI(ImageBase):
    authorized_units = ['label']
    default_values = {'label': 0}
    image_type = "ROI"

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.unit = 'label'
        self.effective_time_h = None
        self.mass_g = None
        self.volume_ml = None

    def __str__(self):
        s = f"ROI: {self.name} unit={self.unit}"
        s += f", Teff = {self.effective_time_h} h"
        if self.mass_g is not None:
            s += f", mass={self.mass_g} g"
        if self.volume_ml is not None:
            s += f", volume={self.volume_ml} ml"
        return s

    def info(self):
        s = super().info() + '\n'
        s += f'Teff:   {self.effective_time_h} h\n'
        s += f'Mass:   {self.mass_g} g\n'
        s += f'Volume: {self.volume_ml} mL'
        return s

    def update_mass_and_volume(self, density_ct):
        # compute mass
        a = sitk.GetArrayViewFromImage(self.image)
        da = sitk.GetArrayViewFromImage(density_ct.image)
        d = da[a == 1]
        self.mass_g = np.sum(d) * self.voxel_volume_ml
        self.volume_ml = len(d) * self.voxel_volume_ml


class ImageDose(ImageBase):
    authorized_units = ['Gy', 'Gy/sec']
    default_values = {'Gy': 0, 'Gy/sec': 0}
    image_type = "Dose"

    def __init__(self):
        super().__init__()
        self.unit = 'Gy'

    def __str__(self):
        s = f"Dose: unit={self.unit}"
        return s


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
