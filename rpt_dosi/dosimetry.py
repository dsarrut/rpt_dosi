import json
from .images import (
    resample_ct_like_spect,
    resample_roi_like_spect,
    convert_ct_to_densities,
)
from .opendose import (
    get_svalue_and_mass_scaling,
    guess_phantom_and_isotope,
)
from .helpers import find_closest_match, print_tests
import SimpleITK as itk
import numpy as np
from datetime import datetime
from box import Box, BoxList


def spect_calibration(spect, calibration_factor, concentration_flag, verbose=True):
    # get voxel volume
    volume_voxel_mL = np.prod(spect.GetSpacing()) / 1000
    arr = itk.GetArrayFromImage(spect)
    total_activity = np.sum(arr) * volume_voxel_mL / calibration_factor
    if verbose:
        print(f"Total activity in the image FOV: {total_activity / 1e6:.2f} MBq")
    # calibration
    if concentration_flag:
        print("Concentration = in Bqml")
        arr = arr / calibration_factor
    else:
        print("Activity = in Bq")
        arr = arr * volume_voxel_mL / calibration_factor

    # create output image
    o = itk.GetImageFromArray(arr)
    o.CopyInformation(spect)
    return o


def spect_Bq_to_SUV(spect, injected_activity_MBq, body_weight_kg):
    # get voxel volume
    volume_voxel_mL = np.prod(spect.GetSpacing()) / 1000
    arr = itk.GetArrayFromImage(spect)
    arr = arr / volume_voxel_mL / (injected_activity_MBq * body_weight_kg)
    # create output image
    o = itk.GetImageFromArray(arr)
    o.CopyInformation(spect)
    return o


def dose_method_hanscheid2017_get_time_eff_h(roi_name):
    # these are some default values
    time_eff_h = {
        "kidney": 50,
        "left kidney": 50,
        "right kidney": 50,
        "liver": 67,
        "spleen": 67,
        "NET tumors": 77
    }
    a, _ = find_closest_match(roi_name, time_eff_h)
    return time_eff_h[a]


def dose_method_hanscheid2017(spect_a, roi_a, acq_time_h, options):
    roi = options.roi
    if "time_eff_h" not in roi:
        if options.radionuclide != "Lu177":
            fatal(f'Radionuclide {options.radionuclide} : unknown time_eff_h, please provide a valid time_eff_h.')
        roi.time_eff_h = dose_method_hanscheid2017_get_time_eff_h(roi.roi_name)
    if options.verbose:
        print(f'Time_eff_h for {roi.roi_name} = {roi.time_eff_h:.3f} h')
    return dose_method_hanscheid2017_equation(spect_a,
                                              roi_a,
                                              acq_time_h,
                                              options.volume_voxel_mL,
                                              roi.time_eff_h)


def dose_method_hanscheid2017_equation(spect_Bq, roi, acq_time_h, volume_voxel_mL, time_eff_h):
    """
    Input img and ROI must be numpy arrays
    """

    # compute mean activity concentration in the ROI
    v = spect_Bq[roi == 1] / volume_voxel_mL
    Ct = np.mean(v) / 1e6

    # compute dose
    dose = 0.125 * Ct * np.power(2, acq_time_h / time_eff_h) * time_eff_h

    return dose


def dose_for_each_rois(
        spect,
        ct,
        rois,
        acq_time_h,
        method,
        options
):
    # options and rois as Box
    options = Box(options)
    rois = BoxList(rois)

    # read spect image from itk to np array
    spect_a = itk.GetArrayFromImage(spect)

    # read and resample ct like spect
    ct_a = resample_ct_like_spect(spect, ct, verbose=options.verbose)
    densities = convert_ct_to_densities(ct_a)

    # pixel volume
    volume_voxel_mL = np.prod(spect.GetSpacing()) / 1000

    # Opendose phantom and radionuclide name
    # (this is not used by all methods)
    if method == "hanscheid2018":
        options.phantom_name, options.rad_name = (
            guess_phantom_and_isotope(options.phantom, options.radionuclide))
        if options.verbose:
            print(f"Phantom = {options.phantom} and isotope = {options.rad_name}")

    # prepare parameters that are used by some methods
    options.densities = densities
    options.volume_voxel_mL = volume_voxel_mL

    # loop on ROI
    results = {"method": method, "date": str(datetime.now())}
    for roi in rois:
        # read roi mask and resample like spect
        r = itk.ReadImage(roi.roi_filename)
        roi_a = resample_roi_like_spect(spect, r, verbose=options.verbose)

        # set options for the current roi
        options.roi = roi

        # go
        dose = None
        if method == "hanscheid2018":
            dose = dose_method_hanscheid2018(spect_a, roi_a, acq_time_h, options)
        if method == "hanscheid2017":
            dose = dose_method_hanscheid2017(spect_a, roi_a, acq_time_h, options)
        if method == "madsen2018":
            dose = dose_method_madsen2018(spect_a, roi_a, acq_time_h, options)

        if dose is None:
            fatal(f"Dosimetry method {method} not known")

        # compute mass of the current ROI
        roi = options.roi
        if "roi_mass" not in roi or "roi_vol" not in roi:
            d = densities[roi_a == 1]
            roi.roi_mass = np.sum(d) * volume_voxel_mL
            roi.roi_vol = len(d) * volume_voxel_mL

        # results
        results[roi.roi_name] = {"dose_Gy": dose, "mass_g": roi.roi_mass, "volume_ml": roi.roi_vol}
    return results


def dose_method_hanscheid2018(spect_a, roi_a, acq_time_h, options):
    # get roi name
    phantom_name, rad_name = guess_phantom_and_isotope(options.phantom, options.radionuclide)
    # get svalues and scaling
    svalue, mass_scaling, roi_mass, roi_vol = get_svalue_and_mass_scaling(
        phantom_name,
        roi_a,
        options.roi.roi_name,
        rad_name,
        options.volume_voxel_mL,
        options.densities,
        verbose=options.verbose,
    )
    options.roi.roi_mass = roi_mass
    options.roi.roi_vol = roi_vol
    # compute the dose
    return dose_method_hanscheid2018_equation(spect_a, roi_a, acq_time_h, svalue, mass_scaling)


def dose_method_hanscheid2018_equation(spect_Bq, roi, acq_time_h, svalue, mass_scaling):
    """
    Input image and ROI must be numpy arrays
    - spect must be in Bq (not concentration)
    - acquisition time in hours
    - output is in Gray
    """
    # compute mean activity in the ROI, in MBq
    v = spect_Bq[roi == 1]
    At = np.sum(v) / 1e6

    # S is in (mGy/MBq/s), so we get dose in mGy
    dose = mass_scaling * At * svalue * (2 * acq_time_h * 3600.0) / np.log(2) / 1000.0

    return dose


def dose_method_madsen2018(spect_a, roi_a, acq_time_h, options):
    roi = options.roi
    # compute mass
    d = options.densities[roi_a == 1]
    roi.roi_mass = np.sum(d) * options.volume_voxel_mL
    roi.roi_vol = len(d) * options.volume_voxel_mL
    # time effective
    if "time_eff_h" not in roi:
        roi.time_eff_h = dose_method_hanscheid2017_get_time_eff_h(options.roi.roi_name)
    if options.verbose:
        print(f'time_eff_h for {roi.roi_name} = {roi.time_eff_h:.3f} h')
    # Delta in mJ MBq-1 h-1 [OpenDose] = mass x Svalue
    if "delta_lu_e" not in options:
        options.delta_lu_e = 0.08532
    if options.verbose:
        print(f'delta_lu_e = {options.delta_lu_e:.3f} mJ MBq-1 h-1')
    # go
    return dose_method_madsen2018_equation(spect_a, roi_a, acq_time_h,
                                           options.delta_lu_e, roi.roi_mass, roi.time_eff_h)


def dose_method_madsen2018_equation(spect_Bq, roi, acq_time_h, delta_lu_e, roi_mass_g, roi_time_eff_h):
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

    # Svalue in mGy MBq-1 h-1
    svalue = delta_lu_e / roi_mass_g * 1000

    # effective clearance rate
    k = np.log(2) / roi_time_eff_h

    # 1Gy = 1J/kg
    integrated_activity = At * np.exp(k * acq_time_h) / k
    dose = integrated_activity * svalue / 1000

    return dose


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
        params = {"A1": A1, "k1": k1, "A2": A2, "k2": k2, "A3": A3, "k3": k3}
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


def test_compare_json_doses(json_ref, json_test):
    with open(json_test) as f:
        dose = json.load(f)
    with open(json_ref) as f:
        dose_ref = json.load(f)
    # remove date key
    del dose["date"]
    del dose_ref["date"]
    # compare
    b = dose == dose_ref
    print_tests(b, f"Compare doses")
    return b
