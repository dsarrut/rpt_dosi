#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.helpers as he
from opengate.contrib.dose.doserate import create_simulation
from opengate.contrib.phantoms.nemaiec import create_material
from box import Box
import SimpleITK as sitk
import numpy as np
import json

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = he.get_tests_folders("test008")
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")
    print()

    """
    voxelize_iec_phantom -s 5 -o data/iec_5mm.mhd --output_source data/iec_5mm_one_source.mhd -a 0 0 0 0 0 1
    voxelize_iec_phantom -s 5 -o data/iec_5mm.mhd --output_source data/iec_5mm_six_sources.mhd -a 6 5 4 3 2 1
    """

    # param
    param = Box({})
    param.visu = False
    param.number_of_threads = 4
    param.verbose = True
    param.radionuclide = "Lu177"
    param.activity_bq = 1e4
    param.ct_image = data_folder / "iec_5mm.mhd"
    param.activity_image = data_folder / "iec_5mm_one_source.mhd"
    param.activity_image = data_folder / "iec_5mm_six_sources.mhd"
    param.output_folder = output_folder
    param.density_tolerance_gcm3 = 0.2
    param.table_mat = he.get_data_folder() / "Schneider2000MaterialsTable.txt"
    param.table_density = he.get_data_folder() / "Schneider2000DensitiesTable.txt"

    # set activity as int (to deal with 1e4 notation)
    param.activity_bq = int(float(param.activity_bq))

    # create the simu
    sim = create_simulation(param)

    # iec material
    create_material(sim)
    iec = sim.volume_manager.get_volume('ct')
    # FIXME to put as a function
    labels = json.loads(open(data_folder / "iec_5mm.json").read())
    iec.voxel_materials = []
    for l in labels:
        mat = "IEC_PLASTIC"
        if "capillary" in l:
            mat = "G4_WATER"
        if "cylinder_hole" in l:
            mat = "G4_LUNG_ICRP"
        if "interior" in l:
            mat = "G4_WATER"
        if "sphere" in l:
            mat = "G4_WATER"
        if "world" in l:
            mat = "G4_AIR"
        if "shell" in l:
            mat = "IEC_PLASTIC"
        if "sphere_37mm" in l:
            mat = "G4_LEAD_OXIDE"
        if "center_cylinder_hole" in l:
            mat = "G4_LEAD_OXIDE"
        iec.voxel_materials.append([labels[l], labels[l] + 1, mat])

    # param
    dose = sim.actor_manager.get_actor_user_info("dose")
    dose.uncertainty = True
    dose.dose = True
    if "six" in str(param.activity_image):
        dose.output = param.output_folder / "iec_six_output.mhd"
    else:
        dose.output = param.output_folder / "iec_one_output.mhd"

    # compute the scaling factor
    spect = sitk.GetArrayFromImage(sitk.ReadImage(param.activity_image))
    total_activity_bq = np.sum(spect)
    scaling = total_activity_bq / float(param.activity_bq * param.number_of_threads)
    print(f'Total activity in image is {total_activity_bq:.0f} Bq, scaling factor is {scaling}')

    # run
    sim.run()

    # print results at the end
    stats = sim.output.get_actor("Stats")
    print(stats)
    stats.write(param.output_folder / "stats.txt")
    print(f"Output in {param.output_folder}")

    # end
    is_ok = False
    he.test_ok(is_ok)
