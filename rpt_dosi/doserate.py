import json
from box import Box
from .utils import check_required_keys
from pathlib import Path
import os
import opengate as gate
from opengate import g4_units
from opengate.geometry.materials import HounsfieldUnit_to_material
from opengate.image import get_translation_between_images_center, read_image_info
import pkg_resources
import SimpleITK as sitk
import numpy as np
import rpt_dosi.images as rim
import rpt_dosi.utils as he


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

    return stats


def sim_add_waterbox(sim, ct_filename):
    wb = sim.add_volume("Box", "waterbox")
    info = read_image_info(ct_filename)
    wb.size = info.size
    wb.material = "G4_WATER"
    wb.color = [0, 0, 1, 1]
    return wb


def simu_add_ct(
    sim, ct_filename, density_tolerance_gcm3, table_mat=None, table_density=None
):
    if sim.visu:
        return sim_add_waterbox(sim, ct_filename)
    ct = sim.add_volume("Image", "ct")
    ct.image = ct_filename
    # material used by default
    ct.material = "G4_AIR"
    gcm3 = g4_units.g_cm3
    tol = density_tolerance_gcm3 * gcm3
    # default tables
    if table_mat is None:
        table_mat = pkg_resources.resource_filename(
            "rpt_dosi", "data/Schneider2000MaterialsTable.txt"
        )
    if table_density is None:
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
        "lu177": {"Z": 71, "A": 177, "name": "Lutetium 177"},
        "y90": {"Z": 39, "A": 90, "name": "Yttrium 90"},
        "in111": {"Z": 49, "A": 111, "name": "Indium 111"},
        "i131": {"Z": 53, "A": 131, "name": "Iodine 131"},
    }

    # Activity source from an image
    source = sim.add_source("VoxelSource", "vox")
    source.attached_to = ct.name
    source.particle = "ion"
    # FIXME proper search function
    source.ion.Z = rad_list[rad.lower()]["Z"]
    source.ion.A = rad_list[rad.lower()]["A"]
    source.image = activity_filename
    source.direction.type = "iso"
    keV = g4_units.keV
    source.energy.mono = 0 * keV
    if ct.name == "ct":
        source.position.translation = get_translation_between_images_center(
            ct.image, activity_filename
        )
    print(f"translation source", source.position.translation)
    return source


def simu_add_dose_actor(sim, ct, source):
    # add dose actor (get the same size as the source)
    source_info = read_image_info(source.image)
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "edep.mhd"
    dose.attached_to = ct.name
    dose.size = source_info.size
    dose.spacing = source_info.spacing
    # translate the dose the same way as the source
    dose.translation = source.position.translation
    print(f"translation dose", dose.translation)
    # set the origin of the dose like the source
    if not sim.phsp_source.visu:
        dose.output_coordinate_system = "attached_to_image"
    dose.hit_type = "random"
    # dose.hit_type = "pre"
    dose.dose_uncertainty.active = True
    dose.dose.active = True
    return dose


def scale_to_absorbed_dose_rate(
    activity,
    dose_in_gray,
    simu_activity,
    calibration_factor,
    verbose=True,
):
    dose_a = sitk.GetArrayFromImage(dose_in_gray)
    activity_a = sitk.GetArrayFromImage(activity)

    volume_voxel_mL = np.prod(activity.GetSpacing()) / 1000
    total_activity = np.sum(activity_a) * volume_voxel_mL / calibration_factor

    if verbose:
        print(f"Total activity in the image FOV: {total_activity / 1e6:.2f} MBq")

    print(f"dose mean = {np.mean(dose_a)} gray.s-1")
    dose_a = dose_a / simu_activity * total_activity
    print(f"dose mean after scaling = {np.mean(dose_a)} gray.s-1")

    # create output image
    o = sitk.GetImageFromArray(dose_a)
    o.CopyInformation(dose_in_gray)
    return o


class DoseRateSimulation:

    def __init__(self, ct_filename, spect_filename):
        self.radionuclide = "Lu177"
        self.activity_bq = 1e4
        self.ct_filename = ct_filename
        self.activity_filename = spect_filename
        self.activity_image = None
        self.output_folder = None
        self.density_tolerance_gcm3 = 0.2
        self.table_mat = he.get_data_folder() / "Schneider2000MaterialsTable.txt"
        self.table_density = he.get_data_folder() / "Schneider2000DensitiesTable.txt"
        # resampling
        self.resample_like = None
        self.gaussian_sigma = None
        # internal
        self.resampled_ct_filename = None
        self.resampled_activity_filename = None

    def resample(self):
        # resample data if needed
        if self.resample_like is not None:
            ct = rim.read_ct(self.ct_filename)
            activity = rim.read_spect(self.activity_filename, unit="Bq")
            activity.require_unit("Bq")
            try:
                sp = [
                    float(self.resample_like),
                    float(self.resample_like),
                    float(self.resample_like),
                ]
                print(f"Resampling from ct to {sp} mm")
                ct = rim.resample_ct_spacing(ct, sp, self.gaussian_sigma)
                print(f"Resampling from activity to {sp} mm (and adjust to ct size)")
                activity = rim.resample_spect_like(activity, ct, self.gaussian_sigma)
            except ValueError:
                if self.resample_like == "ct":
                    print(f"Resampling from spect like ct")
                    activity = rim.resample_spect_like(
                        activity, ct, self.gaussian_sigma
                    )
                else:
                    print(f"Resampling from ct like spect")
                    ct = rim.resample_ct_like(ct, activity, self.gaussian_sigma)
            # save in temporary folder
            self.resampled_ct_filename = self.output_folder / "ct.nii.gz"
            sitk.WriteImage(ct.image, self.resampled_ct_filename)
            self.resampled_activity_filename = self.output_folder / "activity.nii.gz"
            sitk.WriteImage(activity.image, self.resampled_activity_filename)
        else:
            self.resampled_ct_filename = self.ct_filename
            self.resampled_activity_filename = self.activity_filename

    def init_gate_simulation(self, sim):
        self.output_folder = Path(self.output_folder)
        sim.output_dir = Path(self.output_folder)

        # resample ?
        self.resample()

        # create simulation
        stats = simu_default_init(sim)
        ct = simu_add_ct(
            sim,
            self.resampled_ct_filename,
            self.density_tolerance_gcm3,
            self.table_mat,
            self.table_density,
        )
        source = simu_add_activity_source(
            sim, ct, self.resampled_activity_filename, self.radionuclide
        )
        dose = simu_add_dose_actor(sim, ct, source)
        source.activity = self.activity_bq * g4_units.Bq

        # set outputs
        stats.output_filename = "stats.txt"
        dose.output_filename = "output.nii.gz"

        return source

    def compute_scaling(self, sim, unit=None):
        spect = rim.read_spect(self.resampled_activity_filename, unit=unit)
        spect.require_unit("Bq")
        total_activity_bq = spect.compute_total_activity()
        scaling = total_activity_bq / float(self.activity_bq)
        print(
            f"Total activity in image is {total_activity_bq:.0f} Bq, scaling factor is {scaling}"
        )
        print(f"Total number of simulated decay {self.activity_bq} Bq")
        return scaling
