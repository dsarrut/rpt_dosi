import json
from .images import (
    resample_ct_like_spect,
    resample_roi_like_spect,
    convert_ct_to_densities,
)
from .opendose import get_svalue_and_mass_scaling
import SimpleITK as itk
import numpy as np


def spect_calibration(spect, calibration_factor, concentration_flag, verbose=True):
    # get voxel volume
    volume_voxel_mL = np.prod(spect.GetSpacing()) / 1000
    arr = itk.GetArrayFromImage(spect)
    total_activity = np.sum(arr) * volume_voxel_mL / calibration_factor
    if verbose:
        print(f"Total activity in the image FOV: {total_activity / 1e6:.2f} MBq")
    # calibration
    if concentration_flag:
        arr = arr * volume_voxel_mL / calibration_factor
    else:
        arr = arr / calibration_factor

    # create output image
    o = itk.GetImageFromArray(arr)
    o.CopyInformation(spect)
    return o


def dose_hanscheid2018(spect_Bq, roi, time_sec, svalue, mass_scaling):
    """
    Input image and ROI must be numpy arrays
    - spect must be in Bq (not concentration)
    - svalue in mGy/MBq/s
    - time in seconds
    - output is in Gray
    """
    # compute mean activity in the ROI, in MBq
    v = spect_Bq[roi == 1]
    At = np.sum(v) / 1e6

    # S is in (mGy/MBq/s), so we get dose in mGy
    dose = mass_scaling * At * svalue * (2 * time_sec) / np.log(2) / 1000

    return dose


def dose_hanscheid2017(spect_Bqml, roi, time_sec, pixel_volume_ml):
    """
    Input img and ROI must be numpy arrays

    """

    time_h = time_sec / 3600
    time_eff_h = 67.0

    # compute mean activity in the ROI
    v = spect_Bqml[roi == 1] / pixel_volume_ml
    Ct = np.mean(v) / 1e6

    #
    dose = 0.125 * Ct * np.power(2, time_h / time_eff_h) * time_eff_h

    return dose


def dose_hanscheid2018_from_filenames(
        spect_file, ct_file, roi_file, phantom, roi_name, rad_name, time_h
):
    # read spect
    spect = itk.ReadImage(spect_file)
    spect_a = itk.GetArrayFromImage(spect)

    # prepare ct : resample and densities
    ct = itk.ReadImage(ct_file)
    ct_a = resample_ct_like_spect(spect, ct)
    densities = convert_ct_to_densities(ct_a)
    volume_voxel_mL = np.prod(spect.GetSpacing()) / 1000

    # prepare roi : resample
    roi = itk.ReadImage(roi_file)
    roi_a = resample_roi_like_spect(spect, roi)

    # get svalues and scaling
    svalue, mass_scaling = get_svalue_and_mass_scaling(
        phantom, roi_a, roi_name, rad_name, volume_voxel_mL, densities
    )

    # compute dose
    time_sec = time_h * 3600
    dose = dose_hanscheid2018(spect_a, roi_a, time_sec, svalue, mass_scaling)
    print(f"Dose for {roi_file}: {dose:.2f} Gray")
    return dose


def get_roi_list(filename):
    # open the file
    with open(filename, "r") as f:
        data = json.load(f)
    l = []
    for item in data:
        l.append((item["roi_filename"], item["roi_name"]))
    return l


def fit_exp_linear(x, y):
    denegative = 1
    if y[0] < 0:
        denegative = -1
        y[0] = -y[0]
    y = np.log(y)
    k, A_log = np.polyfit(x, y, 1)
    A = np.exp(A_log) * denegative
    if k > 0:
        k = 0
    return A, k


def decay_corrected_tac(t, a, decay_constant):
    return a / np.exp(-decay_constant * t)


def triexpo_fit(times, activities, as_dict=True):
    """
    from https://github.com/jacksonmedphysics/TriExponential-Solver
    Pharmacokinetics backend of the VRAK Voxel dosimetry software reported in
    Med Phys. 2013 Nov;40(11):112503. doi: 10.1118/1.4824318.
    https://www.ncbi.nlm.nih.gov/pubmed/24320462
    """
    t0 = float(times[0])
    t1 = float(times[1])
    t3 = float(times[2])
    d0 = float(activities[0])
    d1 = float(activities[1])
    d3 = float(activities[2])
    if d3 == d1 or d1 == d0 or d0 == d3:
        d0 += 0.0001
        d1 += 0.0002
        d3 += 0.0003
    d1lin = ((d3 - d0) / (t3 - t0)) * t1 + (d0 - ((d3 - d0) / ((t3 - t0)) * t0))
    A3 = d3 / (np.exp(-0.001 * t3))
    d1_lowslope = A3 * np.exp(-0.001 * t1)
    if d1 < d1_lowslope:
        if d0 < d3:
            if d1 < d1lin:
                d1 = d1lin
        else:
            d1 = d1_lowslope
    if d3 < 0.1 * d1:
        d3 = 0.1 * d1
    if d0 < 0.2 * d1:
        d0 = 0.2 * d1
    if d3 > d1:
        k3 = -0.001
        A3 = d3 / (np.exp(k3 * t3))

        x = np.array([t1, t3])
        y = np.array([d1 - (A3 * np.exp(k3 * t1)), 0.01 * d3])
        A2, k2 = fit_exp_linear(x, y)
        if (A2 + A3) < 0:
            A2 = -A3
            A1 = 0
            k1 = 0
        else:
            A1 = -(A2 + A3)
            k1 = -1.3
    else:
        x = np.array([t1, t3])
        y = np.array([d1, d3])
        A3, k3 = fit_exp_linear(x, y)
        if k3 > -0.001:
            k3 = -0.001
            A3 = d3 / (np.exp(k3 * t3))
        x = np.array([t0, t1])
        y = np.array([d0 - (A3 * np.exp(k3 * t0)), 0.01 * d1])
        A2, k2 = fit_exp_linear(x, y)
        if (A2 + A3) < 0:
            A2 = -A3
            A1 = 0
            k1 = 0
        else:
            A1 = -(A2 + A3)
            k1 = -1.3

    if as_dict:
        params = {
            "A1": A1,
            "k1": k1,
            "A2": A2,
            "k2": k2,
            "A3": A3,
            "k3": k3
        }
    else:
        params = np.array([A1, k1, A2, k2, A3, k3])
    return params


def triexpo_rmse(times, activities, decay_constant, A1, k1, A2, k2, A3, k3):
    values = triexpo_apply(times, decay_constant, A1, k1, A2, k2, A3, k3)
    err = np.sqrt(np.sum(np.power(activities - values, 2)) / len(activities))
    return err


def triexpo_param_from_dict(p):
    return p["A1"], p["k1"], p["A2"], p["k2"], p["A3"], p["k3"]


def triexpo_apply_from_dict(x, decay_constant_hours, p):
    return triexpo_apply(x, decay_constant_hours, *triexpo_param_from_dict(p))


def triexpo_apply(x, decay_constant_hours, A1, k1, A2, k2, A3, k3):
    return (
            A1 * np.exp(-(-k1 + decay_constant_hours) * x)
            + A2 * np.exp(-(-k2 + decay_constant_hours) * x)
            + A3 * np.exp(-(-k3 + decay_constant_hours) * x)
    )
