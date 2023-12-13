import setuptools
from setuptools import find_packages

with open("readme.md", "r") as fh:
    long_description = fh.read()

with open("VERSION", "r") as fh:
    version = fh.read()[:-1]

all_packages = find_packages()
selected_packages = []
for p in all_packages:
    if "rpt_dosi" not in p:
        selected_packages.append(p)

setuptools.setup(
    name="rpt_dosi",
    version=version,
    author="David Sarrut",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="RadioPharmaceutical Therapy Dosimetry",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="todo",
    packages=selected_packages,
    python_requires=">=3.7",
    include_package_data=True,
    package_data={
        # Include any data files found in the 'data' directory
        # within the package
        "rpt_dosi": ["data/*.txt"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "click",
        "python-box<7.0.0",
        "numpy",
        "SimpleITK",
        "matplotlib",
        "python-Levenshtein",
        "bs4",
        "selenium",
    ],
    scripts=[
        "bin/rpt_crop_bg",
        "bin/rpt_resample_image",
        "bin/rpt_dose_hanscheid",
        "bin/opendose_web_get_isotopes_list",
        "bin/opendose_web_get_sources_list",
        "bin/opendose_web_get_svalues",
    ],
)
