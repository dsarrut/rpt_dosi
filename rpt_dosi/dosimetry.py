import json
from .images import (
    ImageCT, ImageSPECT, ImageROI,
    resample_ct_like,
    resample_spect_like,
    resample_roi_like,
    resample_dose_like
)
from .opendose import (
    get_svalue_and_mass_scaling,
    guess_phantom_and_isotope,
)
from .helpers import find_closest_match, print_tests, fatal
import SimpleITK as itk
import numpy as np
from datetime import datetime
from box import Box, BoxList
import SimpleITK as sitk


def dose_hanscheid2017(spect_Bq, roi, acq_time_h, volume_voxel_mL, time_eff_h):
    """
    Input img and ROI must be numpy arrays
    """

    # compute mean activity concentration in the ROI
    v = spect_Bq[roi == 1] / volume_voxel_mL
    Ct = np.mean(v) / 1e6

    # compute dose
    dose = 0.125 * Ct * np.power(2, acq_time_h / time_eff_h) * time_eff_h

    return dose


def dose_hanscheid2018(spect_Bq, roi, acq_time_h, svalue, mass_scaling):
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


def dose_madsen2018_dose_rate(dose_rate_a, roi_a, time_from_injection_h, effective_time_h):
    # compute mean dose rate in the ROI in Gy/s
    # convert to hours
    v = dose_rate_a[roi_a == 1]
    dr = np.mean(v) * 3600
    print(f'dr = {dr:.3f} Gy/h')

    # effective clearance rate
    k = np.log(2) / effective_time_h
    print(f'k = {k:.3f} ')

    dose = dr * np.exp(k * time_from_injection_h) / k
    return dose


def dose_madsen2018(spect_Bq, roi, acq_time_h, delta_lu_e, roi_mass_g, roi_time_eff_h):
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
    # print(f'At = {At * 1e6:.3f} Bq')

    # Svalue in mGy MBq-1 h-1
    svalue = delta_lu_e / roi_mass_g * 1000
    # print(f'delta_lu_e = {delta_lu_e:}')
    # print(f'roi_mass_g = {roi_mass_g:}')
    # print(f'svalue = {svalue:}')

    # effective clearance rate
    k = np.log(2) / roi_time_eff_h
    # print(f'k = {k:.3f} ')

    # 1Gy = 1J/kg
    integrated_activity = At * np.exp(k * acq_time_h) / k
    # print(f'ia*svalue = {At * svalue:}')
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


def test_compare_json_doses(json_ref, json_test, tol=0.001):
    with open(json_test) as f:
        dose = json.load(f)
    with open(json_ref) as f:
        dose_ref = json.load(f)
    # remove date key
    k = ['dose_Gy', 'mass_g', 'volume_ml']
    # compare
    is_ok = True
    for roi in dose:
        if not isinstance(dose[roi], dict):
            continue
        roi_ref = dose_ref[roi]
        for v in dose[roi]:
            v1 = float(dose[roi][v])
            v2 = float(roi_ref[v])
            diff = (v1 - v2) / v2
            b = True
            if diff > tol:
                b = False
                is_ok = False
            print_tests(b, f"{roi:<15} {v:<10} : {v1:10.2f} vs {v2:10.2f}  -> {diff * 100:5.2f} % {b}")
    print_tests(is_ok, f"Compare doses (tol={tol})")
    return is_ok


class DoseComputation:
    # name of the method
    name = None

    def __init__(self, ct: ImageCT, spect: ImageSPECT):
        self.ct = ct
        self.spect = spect
        self.resample_like = "ct"
        self.radionuclide = 'lu177'
        self.gaussian_sigma = None

    def check_options(self):
        if self.resample_like != "ct" and self.resample_like != "spect":
            fatal(f"resample_like must be 'ct' or 'spect', while it is '{self.resample_like}'")
        if self.radionuclide != 'lu177':
            fatal(f"radionuclide must be lu177, while it is '{self.radionuclide}")
        if self.spect.time_from_injection_h is None:
            fatal(f"SPECT image must have time_from_injection_h while it is None. {self.spect}")

    def run(self, rois: list[ImageROI]):
        fatal(f'RoiDoseComputation: run must be overwritten')

    def init_resampling(self):
        # resampling (according to the option)
        like = self.spect
        if self.resample_like == "ct":
            like = self.ct
        ct = resample_ct_like(self.ct, like, self.gaussian_sigma)
        spect = resample_spect_like(self.spect, like, self.gaussian_sigma)

        # check spect : must be in Bq
        if spect.unit == "BqmL":
            spect = spect.copy()
            spect.image = spect.image * spect.voxel_volume_ml
            spect.unit = "Bq"
        if spect.unit != "Bq":
            fatal(f'The SPECT unit must be Bq while it is {spect.unit}, cannot compute dose with Madsen2018')

        return ct, spect, like

    def init_results(self):
        results = {"method": self.name,
                   "resampled_like": self.resample_like,
                   "radionuclide": self.radionuclide,
                   "date": str(datetime.now())}
        return Box(results)


class DoseMadsen2018(DoseComputation):
    name = "madsen2018"

    def __init__(self, ct, spect):
        super().__init__(ct, spect)
        self.delta_lu_e = 0.08532

    def run(self, rois: list[ImageROI]):
        self.check_options()
        if self.spect.unit != "Bq":
            raise ValueError(f"The SPECT unit must be Bq, while is {spect.unit}, cannot compute dose.")
        ct, spect, like = self.init_resampling()
        density_ct = ct.compute_densities()

        # compute dose for each roi
        results = self.init_results()
        results["delta_e"] = self.delta_lu_e

        for roi in rois:
            if roi.effective_time_h is None:
                raise ValueError(f'Effective time must be provided for ROI {roi}.')
            roi = resample_roi_like(roi, like)
            roi.update_mass_and_volume(density_ct)
            dose = dose_madsen2018(sitk.GetArrayViewFromImage(spect.image),
                                   sitk.GetArrayViewFromImage(roi.image),
                                   spect.time_from_injection_h,
                                   self.delta_lu_e,
                                   roi.mass_g,
                                   roi.effective_time_h)
            results[roi.name] = {"dose_Gy": dose,
                                 "mass_g": roi.mass_g,
                                 "volume_ml": roi.volume_ml}

        return results


class DoseHanscheid2017(DoseComputation):
    name = "hanscheid2017"

    def __init__(self, ct, spect):
        super().__init__(ct, spect)

    def run(self, rois: list[ImageROI]):
        self.check_options()
        if self.spect.unit != "Bq":
            raise ValueError(f"The SPECT unit must be Bq, while is {spect.unit}, cannot compute dose.")
        ct, spect, like = self.init_resampling()
        density_ct = ct.compute_densities()

        # compute dose for each roi
        results = self.init_results()

        for roi in rois:
            if roi.effective_time_h is None:
                raise ValueError(f'Effective time must be provided for ROI {roi}.')
            roi = resample_roi_like(roi, like)
            roi.update_mass_and_volume(density_ct)
            dose = dose_hanscheid2017(sitk.GetArrayViewFromImage(spect.image),
                                      sitk.GetArrayViewFromImage(roi.image),
                                      spect.time_from_injection_h,
                                      spect.voxel_volume_ml,
                                      roi.effective_time_h)

            results[roi.name] = {"dose_Gy": dose,
                                 "mass_g": roi.mass_g,
                                 "volume_ml": roi.volume_ml}

        return results


class DoseHanscheid2018(DoseComputation):
    name = "hanscheid2018"

    def __init__(self, ct, spect):
        super().__init__(ct, spect)
        self.phantom = None

    def check_options(self):
        super().check_options()
        if self.phantom is None:
            raise ValueError(f'For {self.name}, you need to provide a MIRD phantom')

    def run(self, rois: list[ImageROI]):
        self.check_options()
        if self.spect.unit != "Bq":
            raise ValueError(f"The SPECT unit must be Bq, while is {spect.unit}, cannot compute dose.")
        ct, spect, like = self.init_resampling()
        density_ct = ct.compute_densities()

        # compute dose for each roi
        results = self.init_results()

        # MIRD phantom
        phantom_name, rad_name = guess_phantom_and_isotope(self.phantom, self.radionuclide)
        print(phantom_name, rad_name)

        # loop on roi
        spect_arr = sitk.GetArrayViewFromImage(spect.image)
        for roi in rois:
            roi = resample_roi_like(roi, like)
            roi_arr = sitk.GetArrayViewFromImage(roi.image)
            svalue, mass_scaling, roi.mass_g, roi.volume_ml = get_svalue_and_mass_scaling(
                phantom_name,
                roi_arr,
                roi.name,
                rad_name,
                spect.voxel_volume_ml,
                sitk.GetArrayViewFromImage(density_ct.image),
                verbose=True,
            )
            dose = dose_hanscheid2018(spect_arr,
                                      roi_arr,
                                      spect.time_from_injection_h,
                                      svalue,
                                      mass_scaling)

            results[roi.name] = {"dose_Gy": dose,
                                 "mass_g": roi.mass_g,
                                 "volume_ml": roi.volume_ml}

        return results


class DoseMadsen2018DoseRate(DoseComputation):
    name = "madsen2018_dose_rate"

    def __init__(self, ct, dose_rate):
        super().__init__(ct, dose_rate)
        self.dose_rate = dose_rate
        self.scaling = 1.0

    def init_resampling(self):
        like = self.dose_rate
        if self.resample_like == 'ct':
            like = self.ct
        ct = resample_ct_like(self.ct, like, self.gaussian_sigma)
        dose_rate = resample_dose_like(self.dose_rate, like, self.gaussian_sigma)
        return ct, dose_rate, like

    def run(self, rois: list[ImageROI]):
        self.check_options()
        ct, dose_rate, like = self.init_resampling()
        if dose_rate.unit != "Gy/sec":
            raise ValueError(f"The dose rate unit must be Gy/sec, while is {dose_rate.unit}, cannot compute dose.")
        density_ct = ct.compute_densities()
        dose_rate_arr = sitk.GetArrayViewFromImage(dose_rate.image)

        # compute dose for each roi
        results = self.init_results()

        for roi in rois:
            if roi.effective_time_h is None:
                raise ValueError(f'Effective time must be provided for ROI {roi}.')
            roi = resample_roi_like(roi, like)
            roi.update_mass_and_volume(density_ct)
            dose = dose_madsen2018_dose_rate(dose_rate_arr,
                                             sitk.GetArrayViewFromImage(roi.image),
                                             dose_rate.time_from_injection_h,
                                             roi.effective_time_h)
            dose = dose * self.scaling
            results[roi.name] = {"dose_Gy": dose,
                                 "mass_g": roi.mass_g,
                                 "volume_ml": roi.volume_ml}

        return results


def get_dose_computation_method(name):
    methods = [DoseMadsen2018, DoseHanscheid2017, DoseHanscheid2018, DoseMadsen2018DoseRate]
    for d in methods:
        if d.name.lower() == name.lower():
            return d
    fatal(f'Dose computation method "{name}" not found. '
          f'List of available methods: {[m.name for m in methods]}')
