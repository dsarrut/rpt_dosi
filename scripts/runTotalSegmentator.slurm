#!/bin/bash
#SBATCH -A hbu@v100
#SBATCH -C v100-32g                  # GPU NVIDIA V100 16Gb (exist 32Gb)
#SBATCH --job-name=my_job            # nom du job
#SBATCH --nodes=1                    # on demande 1 node
#SBATCH --ntasks-per-node=1          # nombre total de taches (= nombre de GPU ici)
#SBATCH --gres=gpu:2                 # nombre de GPU (2/4 des GPU)
#SBATCH --cpus-per-task=20           # nombre de coeurs CPU par tache (2/4 du noeud 4-GPU)
# /!\ Attention, "multithread" fait reference à l'hyperthreading dans la terminologie Slurm
#SBATCH --hint=nomultithread         # hyperthreading desactive
#SBATCH --time=01:00:00              # temps maximum d'execution demande (HH:MM:SS)
#SBATCH --output=my_job%j.out      # nom du fichier de sortie
#SBATCH --error=my_job%j.out       # nom du fichier d'erreur (ici commun avec la sortie)

#Run this job with
# sbatch runTotalSegmentator.slurm "/gpfsscratch/rech/hbu/uej68np/totalSegmentator/FY^^/cycle_1/tp1/ct.nii"

grpFolder="hbu"

module purge

# See available module with: module avail
module load gcc/8.3.1 cuda/12.1.0 #python/3.10.4

# Activate venv with this installation and python
#python -m venv env_phd
#pip install cupy itk
cd /gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator
source venv/bin/activate

# For total segmentator, need to define a correct tmp folder to be able to store everything
export TMPDIR="/gpfsscratch/rech/$grpFolder/uej68np/totalSegmentator/tmp"

# Execute your code
file=$1
directory="$(dirname $file)"

cd "$directory"
#TotalSegmentator --task "body" -i "ct.nii" -o "rois"
#TotalSegmentator -i "ct" -o "rois" -ot "dicom"
TotalSegmentator -i "ct.nii" -o "rois2"


