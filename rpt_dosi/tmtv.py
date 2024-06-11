import SimpleITK as sitk
import numpy as np
import rpt_dosi.images as rim
from pathlib import Path


def dilate_mask(itk_image, dilatation_mm):
    # convert radius in vox
    radius = [int(round(dilatation_mm / itk_image.GetSpacing()[0])),
              int(round(dilatation_mm / itk_image.GetSpacing()[1])),
              int(round(dilatation_mm / itk_image.GetSpacing()[2]))]
    # Set the kernel element
    dilate_filter = sitk.BinaryDilateImageFilter()
    dilate_filter.SetKernelRadius(radius)
    dilate_filter.SetKernelType(sitk.sitkBall)
    dilate_filter.SetForegroundValue(1)
    output = dilate_filter.Execute(itk_image)
    return output


def tmtv_mask_cut_the_head(itk_image, mask, skull_filename, margin_mm):
    roi = sitk.ReadImage(skull_filename)
    roi_img = rim.resample_itk_image_like(roi, itk_image, 0, linear=False)
    roi_arr = sitk.GetArrayFromImage(roi_img)
    indices = np.argwhere(roi_arr == 1)
    most_inferior_pixel = indices[np.argmin(indices[:, 0])]
    margin_pix = int(round(margin_mm / itk_image.GetSpacing()[0]))
    most_inferior_pixel[0] -= margin_pix
    mask[most_inferior_pixel[0]:-1, :, :] = 0


def tmtv_apply_mask(itk_image, np_mask):
    # convert img in nparray
    img_np = sitk.GetArrayFromImage(itk_image)

    # apply the mask
    img_np[np_mask == 0] = 0

    # back to itk images
    img = sitk.GetImageFromArray(img_np)
    img.CopyInformation(itk_image)
    return img


def tmtv_mask_threshold(itk_image, mask, threshold):
    # convert img in nparray
    img_np = sitk.GetArrayFromImage(itk_image)

    # threshold the mask
    mask[img_np < threshold] = 0


def tmtv_mask_remove_rois(itk_image, mask, roi_list, roi_folder=""):
    # initialize the mask of removed rois
    removed_roi_mask = np.zeros_like(sitk.GetArrayViewFromImage(itk_image))
    # loop on the roi
    for roi in roi_list:
        # read image
        f = Path(roi_folder) / roi['filename']
        roi_img = sitk.ReadImage(f)
        # check size and resample if needed
        roi_img = rim.resample_itk_image_like(roi_img, itk_image, 0, linear=False)
        # dilatation ?
        roi_img = dilate_mask(roi_img, roi['dilatation'])
        # update the masks
        roi_np = sitk.GetArrayViewFromImage(roi_img)
        mask[roi_np == 1] = 0
        removed_roi_mask[roi_np == 1] = 1
    return removed_roi_mask


class TMTV:
    """
    Compute TMTV Total Metabolic Tumor Volume

    Consider ITK images as input and output here
    """

    def __init__(self):
        self.verbose = True

        # intensity threshold (auto or a value)
        self.intensity_threshold = "auto"

        # remove the head
        self.cut_the_head = False
        self.cut_the_head_margin_mm = 10
        self.cut_the_head_roi_filename = "rois/skull.nii.gz"

        # init default list of roi to be removed
        self.rois_to_remove = []
        self.rois_to_remove_folder = "rois"
        self.default_roi_list()

        # computed param
        self.removed_roi_mask = None

    def default_roi_list(self):
        self.rois_to_remove = [
            {'filename': "liver.nii.gz", 'dilatation': 10},
            {'filename': "kidney_left.nii.gz", 'dilatation': 10},
            {'filename': "kidney_right.nii.gz", 'dilatation': 10},
            {'filename': "spleen.nii.gz", 'dilatation': 10},
            {'filename': "gallbladder.nii.gz", 'dilatation': 5},
            {'filename': "stomach.nii.gz", 'dilatation': 5},
            {'filename': "pancreas.nii.gz", 'dilatation': 5},
            {'filename': "small_bowel.nii.gz", 'dilatation': 5},
            {'filename': "colon.nii.gz", 'dilatation': 5},
            {'filename': "duodenum.nii.gz", 'dilatation': 5},
            {'filename': "urinary_bladder.nii.gz", 'dilatation': 5}
        ]

    def compute_mask(self, itk_image):
        # initialize the mask
        np_mask = np.ones_like(sitk.GetArrayViewFromImage(itk_image))

        # cut the head
        self.verbose and print(f'Cut the head with {self.cut_the_head_margin_mm} mm margin')
        if self.cut_the_head:
            tmtv_mask_cut_the_head(itk_image,
                                   np_mask,
                                   self.cut_the_head_roi_filename,
                                   self.cut_the_head_margin_mm)

        # remove the rois
        self.verbose and print(f'Remove the {len(self.rois_to_remove)} ROIs')
        self.removed_roi_mask = tmtv_mask_remove_rois(itk_image,
                                                      np_mask,
                                                      self.rois_to_remove,
                                                      self.rois_to_remove_folder)

        # threshold
        np_mask = self.apply_threshold(itk_image, np_mask)

        # apply the mask
        itk_tmtv = tmtv_apply_mask(itk_image, np_mask)

        # convert mask to itk image
        itk_mask = sitk.GetImageFromArray(np_mask)
        itk_mask.CopyInformation(itk_image)

        return itk_tmtv, itk_mask

    def apply_threshold(self, itk_image, np_mask):
        image_np = sitk.GetArrayViewFromImage(itk_image)
        if self.intensity_threshold == 'auto':
            v_sum = np.sum(image_np[self.removed_roi_mask == 1])
            n = np.sum(self.removed_roi_mask == 1)
            threshold = v_sum / n
        else:
            threshold = float(self.intensity_threshold)

        # threshold the mask
        self.verbose and print(f'Thresholding with {threshold}')
        np_mask[image_np < threshold] = 0

        return np_mask
