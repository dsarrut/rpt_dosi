## How to start ?

RPT_DOSI is a python toolkit for dosimetry in radionuclide therapy. In practice, it is used for estimating the absorbed dose from SPECT (or PET) images in 177Lu therapy (neurendocrine tumors and prostate cancer with PSMA).

### Installation

The project can be installed as followed:

{tip} We highly recommend creating a specific python environment to 1) be sure all dependencies are handled properly and 2) don't mix with your other Python modules. For example, you can use `venv`. Once the environment is created, you need to activate it:

    python -m venv rpt_dosi_env
    source rpt_dosi_env/bin/activate

or with `conda` environment:

    conda create --name rpt_dosi_env python=3.11
    conda activate rpt_dosi_env

Then, you need to clone the repository and install it (no pypi package yet, but this is planned):

    git clone https://github.com/dsarrut/rpt_dosi.git
    cd rpt_dosi
    pip install -e .

Once installed, we recommend to run the tests:

    rpt_tests

### Quick demo

The toolkit contains Python functions and command linse for several dosimetry methods. Here is a simple example to compute the dose for a ROI (Regions Of Interests) from a SPECT image with the Madsen2018 method:

First, as a command line tool:

    rpt_dose --spect spect.nii.gz --input_unit Bq --ct ct.nii.gz --resample_like spect --time_from_injection_h 24 --method madsen2018 --roi spleen.nii.gz spleen 56 --roi liver.nii.gz liver 67

This command will compute the dose in the SPECT image in the spleen. We explicitly states that the SPECT image is in Bq (not Bq/mL), that the SPECT image was acquired 24 hours after injection, and that the spleen has a Teff (effective clearance time) of 67 hours. We will see later how to store units and metadata in companions files. The inputs are:

- the spect image: spect.nii.gz (it can be any image file format type, such as mhd or mha)
- the pixel unit value for the SPECT : Bq
- the acquisition time of the SPECT image according the injection: 24 hours
- the ct image: ct.nii.gz (the default pixel unit value is HU)
- the mask of the ROI: spleen.nii.gz
- the name of the ROI: spleen
- the effective clearance time of the ROI: 56 (in hours)
- Note: any number of --roi options can be set at the same time 
- the (Single Time Point) method that we use to compute the dose: madsen2018. There are others methods available, type ```rpt_dose -h ``` to get help

The same command can be done via python functions: 

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


