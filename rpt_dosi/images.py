import SimpleITK as sitk
import math
from .helpers import fatal
import numpy as np
import os
import click
import copy


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


class ImageBase:
    def __init__(self):
        self.image = None
        self.filename = None
        self.dicom_folder = None
        self.dicom_filename = None
        self.acquisition_datetime = None
        # internal parameters
        self._unit = None
        self._default_value = 0
        self.authorized_units = []
        self.default_values = {}

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
        self._unit = value
        if value not in self.default_values:
            raise ValueError(f'Undefined default value for unit {value}. Must be one of {self.default_values}')
        self._default_value = self.default_values[value]

    def read(self, filename):
        self.filename = filename
        self.image = sitk.ReadImage(filename)

    def read_dicom(self, filename):
        if os.path.isdir(filename):
            self.dicom_folder = filename
            # FIXME open + unit ?
        if os.path.isfile(filename):
            self.dicom_filename = filename
            # FIXME open + unit ?
        # FIXME error detection


class ImageCT(ImageBase):
    def __init__(self):
        super().__init__()
        self.authorized_units = ['HU', 'gcm3']  # FIXME add attenuation
        self.default_values = {'HU': -1000, 'gcm3': 0}
        self.unit = 'HU'

    def read(self, filename):
        super().read(filename)
        self.unit = 'HU'


class ImageSPECT(ImageBase):
    def __init__(self):
        super().__init__()
        self.injection_datetime = None
        self.injection_activity_Bq = None
        self.time_from_injection_h = 0  # FIXME computed ?
        self.authorized_units = ['Bq', 'BqmL', "counts"]
        self.default_values = {'Bq': 0, 'BqmL': 0, "counts": 0}


class ImageROI(ImageBase):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.unit = 'label'
        self.effective_time_h = 0
        self.authorized_units = ['label']
        self.default_values = {'label': 0}


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


def spect_calibration(img, calibration_factor, verbose):
    imga = sitk.GetArrayFromImage(img)
    volume_voxel_mL = np.prod(img.GetSpacing()) / 1000
    imga = imga * volume_voxel_mL / calibration_factor
    total_activity = np.sum(imga)
    if verbose:
        print(f"Total activity in the image FOV: {total_activity / 1e6:.2f} MBq")
    return imga, total_activity


def convert_ct_to_densities(ct):
    # Simple conversion from HU to g/cm^3
    densities = ct / 1000 + 1
    # the density of air is near 0, not negative
    densities[densities < 0] = 0
    return densities


def resample_ct_like_spect(spect, ct, verbose=True):
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


def resample_ct_spacing(ct: ImageCT, spacing: list[float], gaussian_sigma=None):
    if image_have_same_spacing(ct.image, spacing):
        return
    o = copy.copy(ct)
    o.image = apply_itk_gauss_smoothing(ct.image, gaussian_sigma)
    o.image = resample_itk_image_spacing(o.image, spacing, o.default_value, linear=True)
    return o


def resample_spect_like(spect: ImageSPECT, like: ImageBase):
    if images_have_same_domain(spect.image, like.image):
        return spect
    # resample the image
    o = copy.copy(spect)
    o.image = resample_itk_image_like(spect.image, like.image, o.default_value, linear=True)
    # warning, take the volume into account if needed
    if spect.unit == 'Bq' or spect.unit == 'counts':
        scaling = spect.voxel_volume_ml / like.voxel_volume_ml
        o.image = o.image * scaling
    return o


def resample_roi_like(roi: ImageROI, like: ImageBase):
    if images_have_same_domain(roi.image, like.image):
        return roi
    # resample the image
    default_value = roi.default_value
    g = resample_itk_image_like(roi, like.image, default_value, linear=False)
    return g


def resample_roi_like_spect(spect, roi, convert_to_np=True, verbose=True):
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
    ct_a = resample_ct_like_spect(spect, ct, verbose=False)
    densities = convert_ct_to_densities(ct_a)
    # prepare key
    res = {}
    # loop on rois
    for roi in rois_list:
        # read roi mask and resample like spect
        r = sitk.ReadImage(roi.roi_filename)
        roi_a = resample_roi_like_spect(spect, r, verbose=False)
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


def compare_images(image1, image2):
    img1 = sitk.ReadImage(image1)
    img2 = sitk.ReadImage(image2)
    if not images_have_same_domain(img1, img2):
        print(f"Im1: {img1.GetSize()}  {img1.GetSpacing()}   {img1.GetOrigin()}")
        print(f"Im2: {img2.GetSize()}  {img2.GetSpacing()}   {img2.GetOrigin()}")
        return False
    img1 = sitk.GetArrayFromImage(img1)
    img2 = sitk.GetArrayFromImage(img2)
    return np.all(img1 == img2)


def test_compare_image_exact(image1, image2):
    ok = compare_images(str(image1), str(image2))
    if not ok:
        fatal(
            f"Images {image1} "
            f"and {image2} do not match"
        )
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


def tmtv_mask_cut_the_head(image: object, mask: object, skull_filename: object, margin_mm: object) -> object:
    roi = sitk.ReadImage(skull_filename)
    roi_arr = resample_roi_like_spect(image, roi, convert_to_np=True, verbose=False)
    indices = np.argwhere(roi_arr == 1)
    most_inferior_pixel = indices[np.argmin(indices[:, 0])]
    margin_pix = int(round(margin_mm / image.GetSpacing()[0]))
    most_inferior_pixel[0] -= margin_pix
    mask[most_inferior_pixel[0]:-1, :, :] = 0


def tmtv_apply_mask(image, mask):
    # convert img in nparray
    img_np = sitk.GetArrayFromImage(image)

    # apply the mask
    img_np[mask == 0] = 0

    # back to itk images
    img = sitk.GetImageFromArray(img_np)
    img.CopyInformation(image)
    return img


def tmtv_mask_threshold(image, mask, threshold):
    # convert img in nparray
    img_np = sitk.GetArrayFromImage(image)

    # threshold the mask
    mask[img_np < threshold] = 0


def tmtv_mask_remove_rois(image, mask, roi_list):
    mean_value = 0
    n = 0
    img_np = sitk.GetArrayViewFromImage(image)
    # loop on the roi
    for roi in roi_list:
        # read image
        roi_img = sitk.ReadImage(roi['filename'])
        # check size and resample if needed
        roi_img = resample_roi_like_spect(image, roi_img, convert_to_np=False, verbose=False)
        # dilatation ?
        roi_img = dilate_mask(roi_img, roi['dilatation'])
        # update the mask
        roi_np = sitk.GetArrayViewFromImage(roi_img)
        mask[roi_np == 1] = 0
        # mean value in the roi
        v = img_np[roi_np == 1]
        mean_value += np.sum(v)
        n += len(v)
    mean_value /= n
    return mean_value


def tmtv_compute_mask(image, skull_filename, head_margin_mm, roi_list, threshold, verbose=False):
    # initialize the mask
    mask = np.ones_like(sitk.GetArrayViewFromImage(image))

    # cut the head
    verbose and print(f'Cut the head with {head_margin_mm}mm margin')
    tmtv_mask_cut_the_head(image, mask, skull_filename, margin_mm=head_margin_mm)

    # remove the rois
    verbose and print(f'Remove the {len(roi_list)} ROIs')
    mean_value = tmtv_mask_remove_rois(image, mask, roi_list)

    # threshold
    if threshold == 'auto':
        threshold = mean_value
    else:
        threshold = float(threshold)
    verbose and print(f'Thresholding with {threshold}')
    tmtv_mask_threshold(image, mask, threshold)

    # apply the mask
    tmtv = tmtv_apply_mask(image, mask)

    # convert mask to itk image
    mask = sitk.GetImageFromArray(mask)
    mask.CopyInformation(image)

    return tmtv, mask


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
