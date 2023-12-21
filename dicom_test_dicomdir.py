#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import os
import pydicom
from collections import defaultdict
from tqdm import tqdm
from box import Box
import os
from pydicom import dcmread
from pydicom.fileset import FileSet


# Replace with your DICOM directory
dicom_dir = './dicom/BP102'
dicom_dir = './dicom/LM10'
dicom_dir = './dicom/DG8'
dicom_dir = './dicom/BC4'
dicom_dir = './dicom/DY^^2'

# Create new FileSet
fs = FileSet()

# Directory that contains your DICOM files

# Add DICOM files to FileSet
for dirpath, dirnames, filenames in os.walk(dicom_dir):
    for filename in filenames:
        if filename.endswith('.dcm'):
            filepath = os.path.join(dirpath, filename)
            # Read dataset from DICOM file
            ds = dcmread(filepath)
            # Add all instances inside DICOMDIR file
            fs.add(ds)

# Save FileSet as DICOMDIR to disk
fs.write(f"{dicom_dir}/DICOMDIR")