import SimpleITK as sitk
import math
from .helpers import fatal
import numpy as np
import os


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


def images_have_same_spacing(image1, image2, tolerance=1e-5):
    # Check if the spacing values are close within the given tolerance
    is_same = all(
        math.isclose(i, j, rel_tol=tolerance)
        for i, j in zip(image1.GetSpacing(), image2.GetSpacing())
    )
    return is_same


def resample_image_like(img, like_img, default_pixel_value=-1000, linear=True):
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


def apply_gauss_smoothing(img, sigma):
    gauss_filter = sitk.SmoothingRecursiveGaussianImageFilter()
    gauss_filter.SetSigma(sigma)
    gauss_filter.SetNormalizeAcrossScale(True)
    return gauss_filter.Execute(img)


def resample_image(img, spacing, default_pixel_value=-1000, linear=True):
    # Create a resampler object
    resampler = sitk.ResampleImageFilter()

    # new size
    dim = img.GetDimension()
    new_spacing = [spacing] * dim
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
        ct = apply_gauss_smoothing(ct, sigma)
        ct = resample_image_like(ct, spect, -1000, linear=True)
    ct_a = sitk.GetArrayFromImage(ct)
    return ct_a


def resample_roi_like_spect(spect, roi, convert_to_np=True, verbose=True):
    if not images_have_same_domain(spect, roi):
        if verbose:
            print(
                f"Resample roi mask ({roi.GetSize()}) to spacing={spect.GetSpacing()} size={spect.GetSize()}"
            )
        roi = resample_image_like(roi, spect, 0, linear=False)
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
    # print(f"Compare {image1} {image2}")
    img1 = sitk.ReadImage(image1)
    img2 = sitk.ReadImage(image2)
    if not images_have_same_domain(img1, img2):
        print(f"Im1: {image1.GetSize()}  {image1.GetSpacing()}   {image1.GetOrigin()}")
        print(f"Im2: {image2.GetSize()}  {image2.GetSpacing()}   {image2.GetOrigin()}")
        return False
    img1 = sitk.GetArrayFromImage(img1)
    img2 = sitk.GetArrayFromImage(img2)
    return np.all(img1 == img2)


def test_compare_image_exact(image1, image2):
    ok = compare_images(str(image1), str(image2))
    if not ok:
        try:
            fatal(
                f"Images {os.path.basename(image1)} "
                f"and {os.path.basename(image2)} do not match"
            )
        except:
            pass
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


def tmtv_compute_mask(image, skull_filename, head_margin_mm, roi_list, threshold, verbose=False):
    # initialize the mask
    mask = np.ones_like(sitk.GetArrayViewFromImage(image))

    # cut the head
    verbose and print(f'Cut the head with {head_margin_mm}mm margin')
    tmtv_mask_cut_the_head(image, mask, skull_filename, margin_mm=head_margin_mm)

    # remove the rois
    verbose and print(f'Remove the {len(roi_list)} ROIs')
    tmtv_mask_remove_rois(image, mask, roi_list)

    # threshold
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
