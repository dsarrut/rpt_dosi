## Dosimetry methods

This section focuses on the tools and methods provided by the toolkit for performing dosimetry calculations, i.e. determining the dose absorbed by tissues in radiopharmaceutical therapies. The tools covered here are primarily from the `dosimetry.py` module and the `rpt_dose` command-line tool.

### The `rpt_dose` command line tool, for single time point (STP) methods

The main tool command to compute the absorbed dose in ROI from a single time point SPECT image, is `rpt_dose`: 

```
Usage: rpt_dose [OPTIONS]

Options:
  -s, --spect PATH                Input SPECT image (use --unit to specify the
                                  image)
  -d, --dose_rate PATH            Input dose rate image
  -u, --input_unit [Bq|Bq/mL|SUV|Gy/s]
                                  SPECT or dose rate unit: ['Bq', 'Bq/mL',
                                  'SUV', 'Gy/s']
  -c, --ct PATH                   Input CT image  [required]
  -l, --roi_list TEXT             Filename : list of ROI filename and name
  -r, --roi <TEXT TEXT FLOAT>...  ROI: filename + name + Teff
  -t, --time_from_injection_h FLOAT
                                  Time in h  [required]
  --rad TEXT                      Radionuclide
  -m, --method [hanscheid2017|hanscheid2018|madsen2018|madsen2018_dose_rate]
                                  Which method to use
  -r, --resample_like [spect|ct]  Resample image like spect, dose_rate or ct
  --sigma TEXT                    specify sigma for gauss filter (None=no
                                  gauss, 0 = auto)
  -p, --phantom TEXT              Phantom ICRP 110 AF or AM (only used by some
                                  methods)
  --scaling FLOAT                 Scaling factor (for dose rate)
  -o, --output TEXT               Output json filename
  -h, --help                      Show this message and exit.
```

Here is an example: 

    rpt_dose --spect spect.nii.gz --input_unit Bq --ct ct.nii.gz --resample_like spect --time_from_injection_h 24 --method madsen2018 --roi spleen.nii.gz spleen 56 --roi liver.nii.gz liver 67

If the images are associated with metadata, the options such as unit or time_from_injection are not required. 

ROIs can also be given as a list in a JSON file, for example this file in the tests: [oar.json](https://gitlab.in2p3.fr/tbaudier/rpt_dosi_data/-/blob/main/oar_teff.json).

The current available methods are the following: 

**hanscheid2017** [DOI](https://doi-org.proxy.insermbiblio.inist.fr/10.3413/nukmed-0925-17-08). This method need an estimation of the Teff (effective clearance time) of the organs of interest. The equation is: `dose = 0.125 * Ct * np.power(2, acq_time_h / roi_time_eff_h) * roi_time_eff_h` with Ct the mean activity in the ROI in MBq. 

**hanscheid2018** [DOI](https://doi-org.proxy.insermbiblio.inist.fr/10.2967/jnumed.117.193706). This method used MIRD Svalues and mass scaling of the ROI. Svalue is in mGy/MBq/s and is gathered from the [opendose website](https://www.opendose.org). The equation is: `dose = mass_scaling * At * svalue * (2 * acq_time_h * 3600.0) / np.log(2) / 1000.0` with At the total activity in the ROI (in MBq). The mass scaling is computed according to the reference mass from opendose and the current mass of the ROI computed from the CT. 

**madsen2018** [DOI](https://doi-org.proxy.insermbiblio.inist.fr/10.1002/mp.12886). The computation is as follows. The delta_lu_e value is set to 0.08532 (MIRD, opendose). The effective clearance time of the ROI must be provided (roi_time_eff_h). 

```
    svalue = delta_lu_e / roi_mass_g * 1000
    k = np.log(2) / roi_time_eff_h
    integrated_activity = At * np.exp(k * acq_time_h) / k
    dose = integrated_activity * svalue / 1000
```

Images (and ROI masks) are all resampled like the CT or like the SPECT image. 

Dose computation can also be performed with python scripts as follows:

    ct = rim.read_ct("ct.nii.gz")
    spect = rim.read_spect("spect.nii.gz", "Bq")
    spect.time_from_injection_h = 24.0
    roi1 = read_roi("spleen.nii.gz", "spleen", 56)
    roi2 = read_roi("liver.nii.gz", "liver", 67)

    d = rd.DoseMadsen2018(ct, spect)
    d.resample_like = "spect"
    d.gaussian_sigma = 'auto'
    # the run function takes a list of rois as input
    dose = d.run([roi1, roi2]) 
    print(dose)




### Method with dose rate

TODO