import SimpleITK as itk
import math
from .helpers import fatal
import numpy as np
from datetime import datetime
import pydicom


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
    if not images_have_same_domain(ct, roi):
        fatal(
            f"Cannot set_background for images, the sizes are different"
            f" : {ct.GetSize()} {ct.GetSpacing()} vs {roi.GetSize()} {roi.GetSpacing()}"
        )
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


def spect_calibration(img, calibration_factor, verbose):
    imga = itk.GetArrayFromImage(img)
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
    ct_a = itk.GetArrayFromImage(ct)
    return ct_a


def resample_roi_like_spect(spect, roi, verbose=True):
    if not images_have_same_domain(spect, roi):
        if verbose:
            print(
                f"Resample roi mask ({roi.GetSize()}) to spacing={spect.GetSpacing()} size={spect.GetSize()}"
            )
        roi = resample_image_like(roi, spect, 0, linear=False)
    roi_a = itk.GetArrayFromImage(roi)
    return roi_a


def dicom_read_acquisition_datetime(ds):
    try:
        # extract the date and time
        date = ds.AcquisitionDate  # DICOM date tag (0008,0022)
        time = ds.AcquisitionTime  # DICOM time tag (0008,0032)

        # convert to datetime object
        dt = datetime.strptime(date + time.split(".")[0], "%Y%m%d%H%M%S")
        return {"datetime": str(dt)}
    except:
        fatal(f'Cannot read dicom tag Acquisition Date/Time')


def dicom_read_injection(ds):
    """
    (0054, 0016)  Radiopharmaceutical Information Sequence  1 item(s) ----
       (0018, 0031) Radiopharmaceutical                 LO: 'LU177'
       (0018, 1071) Radiopharmaceutical Volume          DS: '9.5'
       (0018, 1072) Radiopharmaceutical Start Time      TM: '100400.000'
       (0018, 1073) Radiopharmaceutical Stop Time       TM: '100400.000'
       (0018, 1074) Radionuclide Total Dose             DS: '7257.568359375'
       (0018, 1075) Radionuclide Half Life              DS: '574380.0'
       (0018, 1078) Radiopharmaceutical Start DateTime  DT: '20231012100400'
       (0018, 1079) Radiopharmaceutical Stop DateTime   DT: '20231012100400'
       (0054, 0300)  Radionuclide Code Sequence  1 item(s) ----
    """

    try:
        # Read the Radiopharmaceutical Information Sequence tag
        rad_info = ds[(0x0054, 0x0016)].value

        if len(rad_info) != 1:
            fatal(f'The dicom tag Radiopharmaceutical sequence is not equal to 1')

        item = rad_info[0]

        # Read the Radiopharmaceutical tag
        radiopharmaceutical = item[(0x0018, 0x0031)].value

        # Read the Radionuclide Total Dose tag
        total_dose = item[(0x0018, 0x1074)].value

        # Read the Radiopharmaceutical Start DateTime tag
        start_datetime = item[(0x0018, 0x1078)].value
        dt = datetime.strptime(start_datetime, "%Y%m%d%H%M%S")

        return {"radionuclide": radiopharmaceutical,
                "datetime": str(dt),
                "activity_MBq": total_dose
                }
    except:
        fatal(f'Cannot read dicom tag Radiopharmaceutical')


def db_update_injection(db, dicom_ds, cycle_id):
    # extract injeection
    rad = dicom_read_injection(dicom_ds)

    # create cycle if not exist
    if cycle_id not in db["cycles"]:
        db["cycles"][cycle_id] = {}

    # update the db: cycle
    # FIXME maybe check already exist ?
    cycle = db["cycles"][cycle_id]
    cycle['injection'].update(rad)

    return db


def db_update_acquisition(db, dicom_ds, cycle_id, tp_id):
    # extract the date/time
    dt = dicom_read_acquisition_datetime(dicom_ds)

    cycle = db["cycles"][cycle_id]

    # create cycle if not exist
    if tp_id not in cycle['acquisitions']:
        cycle['acquisitions'][tp_id] = {}

    # update the db: acquisition
    acqui = cycle['acquisitions'][tp_id]
    acqui.update(dt)

    return db
