import SimpleITK as itk
import math


def is_image_same_sizes(image1, image2, tolerance=1e-5):
    # Check if the sizes and origins of the images are the same,
    # and if the spacing values are close within the given tolerance
    is_same = (
        len(image1.GetSize()) == len(image2.GetSize())
        and all(i == j for i, j in zip(image1.GetSize(), image2.GetSize()))
        and all(
            math.isclose(i, j, rel_tol=tolerance)
            for i, j in zip(image1.GetSpacing(), image2.GetSpacing())
        )
        and all(
            math.isclose(i, j, rel_tol=tolerance)
            for i, j in zip(image1.GetOrigin(), image2.GetOrigin())
        )
    )
    return is_same


def resample_image_like(img, like_img, default_pixel_value=-1000, linear=True):
    # Create a resampler object
    resampler = itk.ResampleImageFilter()

    # Set the resampler parameters from img1
    resampler.SetSize(like_img.GetSize())
    resampler.SetOutputSpacing(like_img.GetSpacing())
    resampler.SetOutputOrigin(like_img.GetOrigin())
    resampler.SetOutputDirection(like_img.GetDirection())
    resampler.SetDefaultPixelValue(default_pixel_value)

    # Use the identity transform - we only resample in place
    resampler.SetTransform(itk.Transform())

    # Set the interpolation method to Linear
    if linear:
        resampler.SetInterpolator(itk.sitkLinear)

    # Execute the resampling
    resampled_img = resampler.Execute(img)

    return resampled_img


def apply_gauss_smoothing(img, sigma):
    gauss_filter = itk.SmoothingRecursiveGaussianImageFilter()
    gauss_filter.SetSigma(sigma)
    gauss_filter.SetNormalizeAcrossScale(True)
    return gauss_filter.Execute(img)


def resample_image(img, spacing, default_pixel_value=-1000, linear=True):
    # Create a resampler object
    resampler = itk.ResampleImageFilter()

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
    resampler.SetTransform(itk.Transform())

    # Set the interpolation method to Linear
    if linear:
        resampler.SetInterpolator(itk.sitkLinear)

    # Execute the resampling
    resampled_img = resampler.Execute(img)

    return resampled_img


def image_set_background(ct, roi, bg_value=-1000, roi_bg_value=0):
    # get as array
    cta = itk.GetArrayFromImage(ct)
    bga = itk.GetArrayFromImage(roi)
    # set bg
    cta[bga == roi_bg_value] = bg_value
    # back to itk image
    cto = itk.GetImageFromArray(cta)
    cto.CopyInformation(ct)
    return cto


def crop_to_bounding_box(img, bg_value=-1000):
    # Create a binary version of the image (1 where img is not 0, else 0)
    tiny = 1
    binary = itk.BinaryThreshold(
        img,
        lowerThreshold=bg_value + tiny,
        upperThreshold=1e10,
        insideValue=1,
        outsideValue=0,
    )

    # Create a shape statistics object and execute it on the binary image
    shape_stats = itk.LabelShapeStatisticsImageFilter()
    shape_stats.Execute(binary)

    # Get bounding box (you can also add checks here to make sure there is only one label)
    bounding_box = shape_stats.GetBoundingBox(1)

    # Create a region of interest filter and set its region to the bounding box
    roi_filter = itk.RegionOfInterestImageFilter()
    roi_filter.SetRegionOfInterest(bounding_box)

    # Execute filter on original image
    cropped_img = roi_filter.Execute(img)

    return cropped_img


def dose_scale_and_crop(dose, simu_activity, final_activity, roi=None, roi_bg_value=0):
    array = itk.GetArrayFromImage(dose)
    array = array / simu_activity * final_activity
    o = itk.GetImageFromArray(array)
    o.CopyInformation(dose)

    # crop dose in air
    if roi is not None:
        roi = itk.ReadImage(roi)
        if not is_image_same_sizes(dose, roi):
            roi = resample_image_like(
                roi, dose, default_pixel_value=roi_bg_value, linear=True
            )
        o = image_set_background(o, roi, bg_value=0, roi_bg_value=roi_bg_value)

    return o
