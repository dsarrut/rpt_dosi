import SimpleITK as sitk
import numpy as np
import rpt_dosi.images as rim
import rpt_dosi.helpers as rhe
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


def tmtv_mask_remove_rois(itk_image, np_mask, roi_list, roi_folder=""):
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
        np_mask[roi_np == 1] = 0
        removed_roi_mask[roi_np == 1] = 1
    return removed_roi_mask


class TMTV:
    """
    Compute TMTV Total Metabolic Tumor Volume
    Consider ITK images as input and output
    """

    def __init__(self):
        self.verbose = True

        # intensity threshold (auto or a value)
        self.intensity_threshold = "auto"
        self.population_mean_liver = None  # (for gafita2019)

        # remove the head
        self.cut_the_head = False
        self.cut_the_head_margin_mm = 10
        self.cut_the_head_roi_filename = "rois/skull.nii.gz"

        # init default list of roi to be removed
        self.rois_to_remove = []
        self.rois_to_remove_folder = "rois"
        self.rois_to_remove_default()

        # remove areas less than a given volume
        self.minimal_volume_cc = None

        # computed param
        self.removed_rois_mask = None

    def rois_to_remove_default(self):
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
            if self.cut_the_head_roi_filename is None:
               rhe.fatal(f'You need to provide the skull filename')
            tmtv_mask_cut_the_head(itk_image,
                                   np_mask,
                                   self.cut_the_head_roi_filename,
                                   self.cut_the_head_margin_mm)

        # remove the rois
        self.verbose and print(f'Remove {len(self.rois_to_remove)} ROIs (physiological uptake)')
        self.removed_rois_mask = tmtv_mask_remove_rois(itk_image,
                                                       np_mask,
                                                       self.rois_to_remove,
                                                       self.rois_to_remove_folder)

        # threshold
        np_mask = self.apply_threshold(itk_image, np_mask)

        # convert mask to itk image
        itk_mask = sitk.GetImageFromArray(np_mask)
        itk_mask.CopyInformation(itk_image)

        # keep areas with a minimal volume
        (self.verbose and self.minimal_volume_cc is not None
         and print(f'Remove areas below {self.minimal_volume_cc} cc'))
        itk_mask = remove_small_areas(itk_mask, self.minimal_volume_cc, keep_binary_mask=True)

        # apply the mask
        itk_tmtv = tmtv_apply_mask(itk_image, np_mask)

        return itk_tmtv, itk_mask

    def apply_threshold(self, itk_image, np_mask):
        np_image = sitk.GetArrayViewFromImage(itk_image)
        threshold = None
        try:
            self.intensity_threshold = float(self.intensity_threshold)
        except:
            pass
        if is_number(self.intensity_threshold):
            threshold = float(self.intensity_threshold)
        else:
            methods = ['auto', 'gafita2019']
            if self.intensity_threshold not in methods:
                rhe.fatal(f'Threshold must be a number or {methods} '
                          f'while it is {self.intensity_threshold}')
            if self.intensity_threshold == 'auto':
                threshold = self.get_removed_rois_mean_value(np_image)
            if self.intensity_threshold == 'gafita2019':
                threshold = self.get_gafita2019_threshold(itk_image, self.population_mean_liver)

        # threshold the mask
        self.verbose and print(f'Thresholding with {threshold}')
        np_mask[np_image < threshold] = 0

        return np_mask

    def get_removed_rois_mean_value(self, np_image):
        v_sum = np.sum(np_image[self.removed_rois_mask == 1])
        n = np.sum(self.removed_rois_mask == 1)
        return v_sum / n

    def get_gafita2019_threshold(self, itk_image, population_mean_liver):
        if population_mean_liver is None:
            rhe.fatal(f'For gafita2019 method, population_mean_liver must be provided')
        population_mean_liver = float(population_mean_liver)
        # we assume one roi is the liver
        liver_roi = None
        for roi in self.rois_to_remove:
            if 'liver' in roi['filename']:
                liver_roi = roi
        if liver_roi is None:
            rhe.fatal(f'Cannot find liver ROI in {self.rois_to_remove_folder}')
        roi_list = [liver_roi]

        # get the mean intensity in the liver
        np_mask = np.ones_like(sitk.GetArrayViewFromImage(itk_image))
        liver_mask = tmtv_mask_remove_rois(itk_image,
                                           np_mask,
                                           roi_list,
                                           roi_folder=self.rois_to_remove_folder)
        np_image = sitk.GetArrayViewFromImage(itk_image)
        mean_liver = np_image[liver_mask == 1].mean()
        std_liver = np_image[liver_mask == 1].std()
        self.verbose and print(
            f'Computed mean/std liver: {mean_liver} {std_liver}, population mean: {population_mean_liver=}')

        # compute threshold
        threshold = (population_mean_liver / mean_liver) * (mean_liver + std_liver)
        return threshold


def is_number(n):
    return isinstance(n, (int, float))


def remove_small_areas(itk_mask, minimal_volume_cc, keep_binary_mask=True):
    if minimal_volume_cc is None:
        return itk_mask
    minimal_volume_cc = float(minimal_volume_cc)

    # convert mask image into char
    mask = sitk.Cast(itk_mask, sitk.sitkInt8)

    # connected component labelling
    ccl = sitk.ConnectedComponent(mask)

    # Keep only labels with more than a given size
    volume_cc = float(np.prod(itk_mask.GetSpacing())) * 0.001
    max_size = int(minimal_volume_cc / volume_cc)
    ccl = sitk.RelabelComponent(ccl, minimumObjectSize=max_size, sortByObjectSize=True)

    # back to binary mask ?
    if keep_binary_mask:
        np_mask = sitk.GetArrayFromImage(ccl)
        np_mask[np_mask != 0] = 1
        a = sitk.GetImageFromArray(np_mask)
        a.CopyInformation(ccl)
        ccl = a

    return ccl


def find_foci(tmtv, tmtv_mask, min_size_cm3=1, percentage_threshold=0.001):
    # get the sitk image
    mask = tmtv_mask.image

    # convert mask image into char
    mask = sitk.Cast(mask, sitk.sitkInt8)

    # pre-processing, image closing
    # radius = [2, 2, 2]
    # mask = sitk.BinaryMorphologicalClosing(mask, radius)
    # mask = sitk.BinaryMorphologicalOpening(mask, radius)

    # find foci with connected component labelling
    foci = sitk.ConnectedComponent(mask)

    # relabel by size
    foci = sitk.RelabelComponent(foci, sortByObjectSize=True)

    # Get the shape statistics of the labels using
    # (not needed for the final version)
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(foci)
    print(f'Number of labels = {stats.GetNumberOfLabels()}')

    # Keep only labels with more than a given size
    volume = tmtv_mask.voxel_volume_cc
    max_size = int(min_size_cm3 / volume)
    print(f'{min_size_cm3=} -> {max_size=} pixels')
    foci = sitk.RelabelComponent(foci, minimumObjectSize=max_size)

    # relabel
    # (not needed for the final version)
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(foci)
    print(f'Number of labels = {stats.GetNumberOfLabels()}')

    # keep labels only if max intensity
    spect = tmtv.image
    spect_arr = sitk.GetArrayViewFromImage(spect)
    foci_arr = sitk.GetArrayFromImage(foci)
    total_max_intensity = np.max(spect_arr)
    print(f'{total_max_intensity=}')

    # Keep only labels where the maximum intensity exceeds the threshold
    for l in stats.GetLabels():
        # select pixels at the label
        label_arr = spect_arr[foci_arr == l]
        # print(f'{len(label_arr)=}')
        max_intensity = np.max(label_arr)
        # Check if the maximum intensity exceeds the threshold
        if max_intensity <= (percentage_threshold * total_max_intensity):
            foci_arr[foci_arr == l] = 0
            print(f'remove {l} {max_intensity=} vs {total_max_intensity}  --->   {max_intensity / total_max_intensity}')

    # Keep only the labels to be retained
    a = sitk.GetImageFromArray(foci_arr)
    a.CopyInformation(foci)
    foci = a

    # relabel
    # (not needed for the final version)
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(foci)
    print(f'Number of labels = {stats.GetNumberOfLabels()}')

    return foci


def get_label_centroids(foci):
    # Create an empty list to store centroids
    centroids = []

    # Get the shape statistics of the labels using LabelShapeStatisticsImageFilter
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(foci)

    # Iterate over the labels
    for label in stats.GetLabels():
        # Get the centroid of the label
        centroid = stats.GetCentroid(label)
        centroids.append(centroid)

    return centroids
