import os
import itk
import numpy as np
import rt_utils
import click
import glob
import gatetools as gt
import tqdm

def image_to_dicom_rt_struct(dicom, mask, output):

    #Read dicom input
    series = gt.separate_series(dicom)
    if len(series.keys()) != 1:
        logger.error('The number of dicom serie detected is not 1')
        return
    seriesInstanceUID = list(series.keys())[0]
    if len(series[seriesInstanceUID]) > 1:
        dicomImage = gt.read_dicom(series[seriesInstanceUID])
    elif len(series[seriesInstanceUID]) == 1 and series[seriesInstanceUID][0].endswith(".dcm"):
        dicomImage = gt.read_3d_dicom(series[seriesInstanceUID])
    else:
        logger.error('no input available')
        return
    dicomFolder = os.path.dirname(dicom[0])

    rtstruct = rt_utils.RTStructBuilder.create_new(
      dicom_series_path=dicomFolder,
    )

    maskFiles = glob.glob(mask + "/*.nii.gz")
    for maskFile in tqdm.tqdm(maskFiles):
        maskImage = itk.imread(maskFile)
        segArray = itk.array_from_image(maskImage)
        segArray = segArray.astype(np.bool)
        segArray = np.swapaxes(segArray,0,2)
        segArray = np.swapaxes(segArray,0,1)

        name = os.path.basename(maskFile)[:-7]

        rtstruct.add_roi(
          mask=segArray,
          color=[255, 0, 255],
          name=name,
          approximate_contours=False
        )

    rtstruct.save(output)

# -----------------------------------------------------------------------------
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)

@click.option('--mask','-m', help='Input mask folder', required=True,
              type=click.Path(dir_okay=True))
@click.option('--output','-o', help='Output dicom RTStruct filename',
              type=click.Path(dir_okay=False,
                              writable=True, readable=False,
                              resolve_path=True, allow_dash=False, path_type=None))
@click.argument('dicom', type=str, required=True, nargs=-1)

@gt.add_options(gt.common_options)
def image_to_dicom_rt_struct_main(mask, output, dicom, **kwargs):
    '''
    Tool to convert a binary mask image (mhd, ...) to RTStruct. It uses the python tool rt_utils
    The mask and the image from dicom must have the same spacing/size/origin. The resample is done automatically if needed

    eg:

    gt_image_to_dicom_rt_struct -m path/to/binary/ -o path/to/output path/to/ct/dicom/*.dcm

    '''

    image_to_dicom_rt_struct(dicom, mask, output)

# -----------------------------------------------------------------------------
if __name__ == '__main__':
    image_to_dicom_rt_struct_main()





