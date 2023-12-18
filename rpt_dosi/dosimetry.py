import json
from box import Box
from .helpers import check_required_keys, fatal
from .images import (
    resample_ct_like_spect,
    resample_roi_like_spect,
    convert_ct_to_densities,
)
from .opendose import get_svalue_and_mass_scaling
from pathlib import Path
import os
import opengate as gate
from opengate import g4_units
from opengate.geometry.materials import HounsfieldUnit_to_material
from opengate.image import get_translation_between_images_center, read_image_info
import pkg_resources
import SimpleITK as itk
import numpy as np


def read_dose_rate_options(json_file):
    print(json_file)
    if json_file is None:
        options = init_dose_rate_options()
    else:
        f = open(json_file).read()
        options = Box(json.loads(f))
    check_dose_rate_options(options)
    return options


def check_dose_rate_options(options):
    ref = init_dose_rate_options()
    check_required_keys(options, ref.keys())


def init_dose_rate_options():
    options = Box()
    options.number_of_threads = 1
    options.density_tolerance_gcm3 = 0.1
    return options


def get_timepoint_output_folder(output_folder, cycle, timepoint, name="doserate"):
    folder = (
            Path(output_folder)
            / Path(cycle.cycle_id)
            / Path(timepoint.acquisition_id)
            / name
    )
    os.makedirs(folder, exist_ok=True)
    return folder


def simu_default_init(sim):
    sim.visu_type = "vrml"
    m = gate.g4_units.m
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # cuts
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.set_production_cut("world", "all", 1 * m)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output = "stats.txt"


def sim_add_waterbox(sim, ct_filename):
    wb = sim.add_volume("Box", "waterbox")
    info = read_image_info(ct_filename)
    wb.size = info.size
    wb.material = "G4_WATER"
    wb.color = [0, 0, 1, 1]
    return wb


def simu_add_ct(sim, ct_filename, density_tolerance_gcm3):
    if sim.visu:
        return sim_add_waterbox(sim, ct_filename)
    ct = sim.add_volume("Image", "ct")
    ct.image = ct_filename
    # material used by default
    ct.material = "G4_AIR"
    gcm3 = g4_units.g_cm3
    tol = density_tolerance_gcm3 * gcm3
    # default tables
    table_mat = pkg_resources.resource_filename(
        "rpt_dosi", "data/Schneider2000MaterialsTable.txt"
    )
    table_density = pkg_resources.resource_filename(
        "rpt_dosi", "data/Schneider2000DensitiesTable.txt"
    )
    ct.voxel_materials, materials = HounsfieldUnit_to_material(
        sim, tol, table_mat, table_density
    )
    print(f"Density tolerance = {tol / gcm3} gcm3")
    print(f"Number of materials in the CT : {len(ct.voxel_materials)} materials")
    # ct.dump_label_image = "labels.mhd"

    # production cut
    mm = gate.g4_units.mm
    sim.physics_manager.set_production_cut("ct", "all", 1 * mm)
    return ct


def simu_add_activity_source(
        sim,
        ct,
        activity_filename,
        rad,
):
    rad_list = {
        "Lu177": {"Z": 71, "A": 177, "name": "Lutetium 177"},
        "Y90": {"Z": 39, "A": 90, "name": "Yttrium 90"},
        "In111": {"Z": 49, "A": 111, "name": "Indium 111"},
        "I131": {"Z": 53, "A": 131, "name": "Iodine 131"},
    }

    # Activity source from an image
    source = sim.add_source("VoxelsSource", "vox")
    source.mother = ct.name
    source.particle = "ion"
    source.ion.Z = rad_list[rad]["Z"]
    source.ion.A = rad_list[rad]["A"]
    source.image = activity_filename
    source.direction.type = "iso"
    keV = g4_units.keV
    source.energy.mono = 0 * keV
    if ct.name == "ct":
        source.position.translation = get_translation_between_images_center(
            ct.image, activity_filename
        )
    return source


def add_dose_actor(sim, ct, source):
    # add dose actor (get the same size as the source)
    source_info = read_image_info(source.image)
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = "edep.mhd"
    dose.mother = ct.name
    dose.size = source_info.size
    dose.spacing = source_info.spacing
    # translate the dose the same way as the source
    dose.translation = source.position.translation
    # set the origin of the dose like the source
    if not sim.user_info.visu:
        dose.img_coord_system = True
    dose.hit_type = "random"
    # dose.hit_type = "pre"
    dose.uncertainty = True
    dose.square = True
    dose.gray = True
    return dose


def scale_to_absorbed_dose_rate(
        activity,
        dose_in_gray,
        simu_activity,
        calibration_factor,
        verbose=True,
):
    dose_a = itk.GetArrayFromImage(dose_in_gray)
    activity_a = itk.GetArrayFromImage(activity)

    volume_voxel_mL = np.prod(activity.GetSpacing()) / 1000
    total_activity = np.sum(activity_a) * volume_voxel_mL / calibration_factor

    if verbose:
        print(f"Total activity in the image FOV: {total_activity / 1e6:.2f} MBq")

    print(f"dose mean = {np.mean(dose_a)} gray.s-1")
    dose_a = dose_a / simu_activity * total_activity
    print(f"dose mean after scaling = {np.mean(dose_a)} gray.s-1")

    # create output image
    o = itk.GetImageFromArray(dose_a)
    o.CopyInformation(dose_in_gray)
    return o


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


def fit_triexpo(times, activities):
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
    d1lin = (((d3 - d0) / (t3 - t0)) * t1 + (d0 - ((d3 - d0) / ((t3 - t0)) * t0)))
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
    params = np.array([A1, k1, A2, k2, A3, k3])
    return params
