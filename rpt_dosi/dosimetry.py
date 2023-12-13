import json
from box import Box
from .helpers import check_required_keys, fatal
from .images import images_have_same_domain, resample_image_like, image_set_background
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
    print(f"Density tolerance = {tol/gcm3} gcm3")
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
        print(f"Total activity in the image FOV: {total_activity/1e6:.2f} MBq")

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
        print(f"Total activity in the image FOV: {total_activity/1e6:.2f} MBq")
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


def dose_hanscheid2017(img, roi, time_sec, pixel_volume_ml):
    """
    Input img and ROI must be numpy arrays

    """

    time_h = time_sec / 3600
    time_eff_h = 67.0

    # compute mean activity in the ROI
    v = img[roi == 1] / pixel_volume_ml
    Ct = np.mean(v) / 1e6

    #
    dose = 0.125 * Ct * np.power(2, time_h / time_eff_h) * time_eff_h

    return dose
