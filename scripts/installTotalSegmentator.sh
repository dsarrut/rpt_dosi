
grpFolder="hbu"

#1st step: Create the venv
rm -rf /gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator
mkdir /gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator
cd /gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator
module purge
module load gcc/8.3.1 cuda/12.1.0 python/3.10.4
python -m venv venv
source venv/bin/activate

#2nd step: Instal total segmentator
# With pip installation, the wheels are downloaded in ~/.cache/pip , without a lot of space. TotalSegmentator is heavy, it's necessary to remove the content of that folder before pip installation
pip install --upgrade pip
rm -rf ~/.cache/pip/*
pip install numpy
rm -rf ~/.cache/pip/*
pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu121 #have to install torch manually to match the cuda version chosen during the module load
rm -rf ~/.cache/pip/*
pip install TotalSegmentator
rm -rf ~/.cache/pip/*
pip install gatetools
rm -rf ~/.cache/pip/*

#3rd step: Downloading of total segmentator data
# By default, the data are in ~/.totalsegmentator , without a lot of space. So we create a symbolic link
rm ~/.totalsegmentator
mkdir /gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator/dataTotalSegmentator
ln -s /gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator/dataTotalSegmentator ~/.totalsegmentator
rm -rf /gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator/tmp
mkdir /gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator/tmp
# Jean Zay does not have internet connection during a job, so we need to download the data beafore. Stop the run when it's printed "resampling"
mkdir segmentations
gt_image_convert -o ct.nii ct.mhd
TotalSegmentator --fast -i ct.nii -o segmentations
TotalSegmentator -i ct.nii -o segmentations

#4th step: job
# Disconnect/Connect to have a clean environement
sbatch runTotalSegmentator.slurm 

