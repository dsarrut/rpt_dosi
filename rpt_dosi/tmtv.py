import SimpleITK as sitk
import numpy as np
import rpt_dosi.images as rim
import rpt_dosi.utils as rhe
from pathlib import Path


def dilate_mask(itk_image, dilatation_mm):
    if dilatation_mm == 0:
        return itk_image
    # convert radius in vox
    radius = [
        int(round(dilatation_mm / itk_image.GetSpacing()[0])),
        int(round(dilatation_mm / itk_image.GetSpacing()[1])),
        int(round(dilatation_mm / itk_image.GetSpacing()[2])),
    ]
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
    mask[most_inferior_pixel[0] : -1, :, :] = 0


def tmtv_apply_mask(itk_image, np_mask):
    # convert img in nparray
    img_np = sitk.GetArrayFromImage(itk_image)

    # apply the mask
    img_np[np_mask == 0] = 0

    # back to itk images
    img = sitk.GetImageFromArray(img_np)
    img.CopyInformation(itk_image)
    return img


def tmtv_mask_remove_rois(itk_image, np_mask, roi_list, roi_folder="", verbose=False):
    nb_pixels = itk_image.GetNumberOfPixels()
    mask = np.zeros_like(sitk.GetArrayViewFromImage(itk_image))
    # loop on the roi
    for roi in roi_list:
        # read image
        print(roi_folder, roi["filename"])
        f = Path(roi_folder) / roi["filename"]
        roi_img = sitk.ReadImage(f)
        roi_nb_pixels = roi_img.GetNumberOfPixels()
        if verbose:
            print(f'Removing {f}, resample and dilate {roi["dilatation"]}')
        # dilate or resample first (dilatation is slow, so we apply on the smallest image)
        if roi_nb_pixels > nb_pixels:
            # check size and resample if needed
            roi_img = rim.resample_itk_image_like(roi_img, itk_image, 0, linear=False)
            # dilatation ?
            roi_img = dilate_mask(roi_img, roi["dilatation"])
        else:
            # dilatation ?
            roi_img = dilate_mask(roi_img, roi["dilatation"])
            # check size and resample if needed
            roi_img = rim.resample_itk_image_like(roi_img, itk_image, 0, linear=False)
        # update the masks
        roi_np = sitk.GetArrayViewFromImage(roi_img)
        np_mask[roi_np == 1] = 0
        mask[roi_np == 1] = 1
    return mask


def tmtv_mask_keep_rois(itk_image, np_mask, roi_list, roi_folder="", verbose=False):
    # loop on the roi
    for roi in roi_list:
        # read image
        f = Path(roi_folder) / roi["filename"]
        if verbose:
            print(f"Keeping {f} (resample)")
        roi_img = sitk.ReadImage(f)
        # check size and resample if needed
        roi_img = rim.resample_itk_image_like(roi_img, itk_image, 0, linear=False)
        # update the masks
        roi_np = sitk.GetArrayViewFromImage(roi_img)
        np_mask[roi_np == 1] = 1


def rois_to_remove_default():
    return [
        {"filename": "liver.nii.gz", "dilatation": 10},
        {"filename": "kidney_left.nii.gz", "dilatation": 10},
        {"filename": "kidney_right.nii.gz", "dilatation": 10},
        {"filename": "spleen.nii.gz", "dilatation": 10},
        {"filename": "gallbladder.nii.gz", "dilatation": 5},
        {"filename": "stomach.nii.gz", "dilatation": 5},
        {"filename": "pancreas.nii.gz", "dilatation": 5},
        {"filename": "small_bowel.nii.gz", "dilatation": 5},
        {"filename": "colon.nii.gz", "dilatation": 5},
        {"filename": "duodenum.nii.gz", "dilatation": 5},
        {"filename": "urinary_bladder.nii.gz", "dilatation": 5},
    ]


def rois_to_keep_default():
    # rois = ["clavicula", "femur", "hip_", "humerus", "rib_", "vertebrae", "sacrum", "scapula"]
    return [
        {"filename": "clavicula_left_crop.nii.gz"},
        {"filename": "clavicula_right_crop.nii.gz"},
        {"filename": "femur_left_crop.nii.gz"},
        {"filename": "femur_right_crop.nii.gz"},
        {"filename": "hip_left_crop.nii.gz"},
        {"filename": "hip_right_crop.nii.gz"},
        {"filename": "humerus_left_crop.nii.gz"},
        {"filename": "humerus_right_crop.nii.gz"},
        {"filename": "rib_left_1_crop.nii.gz"},
        {"filename": "rib_left_10_crop.nii.gz"},
        {"filename": "rib_left_11_crop.nii.gz"},
        {"filename": "rib_left_12_crop.nii.gz"},
        {"filename": "rib_left_2_crop.nii.gz"},
        {"filename": "rib_left_3_crop.nii.gz"},
        {"filename": "rib_left_4_crop.nii.gz"},
        {"filename": "rib_left_5_crop.nii.gz"},
        {"filename": "rib_left_6_crop.nii.gz"},
        {"filename": "rib_left_7_crop.nii.gz"},
        {"filename": "rib_left_8_crop.nii.gz"},
        {"filename": "rib_left_9_crop.nii.gz"},
        {"filename": "rib_right_1_crop.nii.gz"},
        {"filename": "rib_right_10_crop.nii.gz"},
        {"filename": "rib_right_11_crop.nii.gz"},
        {"filename": "rib_right_12_crop.nii.gz"},
        {"filename": "rib_right_2_crop.nii.gz"},
        {"filename": "rib_right_3_crop.nii.gz"},
        {"filename": "rib_right_4_crop.nii.gz"},
        {"filename": "rib_right_5_crop.nii.gz"},
        {"filename": "rib_right_6_crop.nii.gz"},
        {"filename": "rib_right_7_crop.nii.gz"},
        {"filename": "rib_right_8_crop.nii.gz"},
        {"filename": "rib_right_9_crop.nii.gz"},
        {"filename": "sacrum_crop.nii.gz"},
        {"filename": "scapula_left_crop.nii.gz"},
        {"filename": "scapula_right_crop.nii.gz"},
        {"filename": "vertebrae_C1_crop.nii.gz"},
        {"filename": "vertebrae_C2_crop.nii.gz"},
        {"filename": "vertebrae_C3_crop.nii.gz"},
        {"filename": "vertebrae_C4_crop.nii.gz"},
        {"filename": "vertebrae_C5_crop.nii.gz"},
        {"filename": "vertebrae_C6_crop.nii.gz"},
        {"filename": "vertebrae_C7_crop.nii.gz"},
        {"filename": "vertebrae_L1_crop.nii.gz"},
        {"filename": "vertebrae_L2_crop.nii.gz"},
        {"filename": "vertebrae_L3_crop.nii.gz"},
        {"filename": "vertebrae_L4_crop.nii.gz"},
        {"filename": "vertebrae_L5_crop.nii.gz"},
        {"filename": "vertebrae_S1_crop.nii.gz"},
        {"filename": "vertebrae_T1_crop.nii.gz"},
        {"filename": "vertebrae_T10_crop.nii.gz"},
        {"filename": "vertebrae_T11_crop.nii.gz"},
        {"filename": "vertebrae_T12_crop.nii.gz"},
        {"filename": "vertebrae_T2_crop.nii.gz"},
        {"filename": "vertebrae_T3_crop.nii.gz"},
        {"filename": "vertebrae_T4_crop.nii.gz"},
        {"filename": "vertebrae_T5_crop.nii.gz"},
        {"filename": "vertebrae_T6_crop.nii.gz"},
        {"filename": "vertebrae_T7_crop.nii.gz"},
        {"filename": "vertebrae_T8_crop.nii.gz"},
        {"filename": "vertebrae_T9_crop.nii.gz"},
    ]


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
        self.rois_to_remove = rois_to_remove_default()
        self.rois_to_remove_folder = "rois"
        self.removed_mask = None

        # init default list of roi to keep
        self.rois_to_keep = []
        self.rois_to_keep_folder = "rois"

        # remove areas less than a given volume
        self.minimal_volume_cc = None

        # computed param
        self.tmtv_mask_np = None

    def compute_mask(self, itk_image):
        # initialize the mask
        self.tmtv_mask_np = np.ones_like(sitk.GetArrayViewFromImage(itk_image))

        # cut the head
        if self.verbose:
            print(f"Cut the head with {self.cut_the_head_margin_mm} mm margin")
        if self.cut_the_head:
            if self.cut_the_head_roi_filename is None:
                rhe.fatal(f"You need to provide the skull filename")
            tmtv_mask_cut_the_head(
                itk_image,
                self.tmtv_mask_np,
                self.cut_the_head_roi_filename,
                self.cut_the_head_margin_mm,
            )

        # remove some rois
        if self.verbose:
            print(f"Remove {len(self.rois_to_remove)} ROIs (physiological uptake)")
        self.removed_mask = tmtv_mask_remove_rois(
            itk_image,
            self.tmtv_mask_np,
            self.rois_to_remove,
            self.rois_to_remove_folder,
            self.verbose,
        )

        # keep some rois
        if self.rois_to_keep is not None:
            if self.verbose:
                print(f"Keep {len(self.rois_to_keep)} ROIs")
            tmtv_mask_keep_rois(
                itk_image,
                self.tmtv_mask_np,
                self.rois_to_keep,
                self.rois_to_keep_folder,
                self.verbose,
            )

        # threshold
        self.tmtv_mask_np = self.apply_threshold(itk_image, self.tmtv_mask_np)

        # convert mask to itk image
        itk_mask = sitk.GetImageFromArray(self.tmtv_mask_np)
        itk_mask.CopyInformation(itk_image)

        # keep areas with a minimal volume
        if self.verbose and self.minimal_volume_cc is not None:
            print(f"Remove areas below {self.minimal_volume_cc} cc")
        itk_mask = remove_small_areas(
            itk_mask, self.minimal_volume_cc, keep_binary_mask=True
        )

        # apply the mask
        itk_tmtv = tmtv_apply_mask(itk_image, self.tmtv_mask_np)

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
            methods = ["auto", "gafita2019"]
            if self.intensity_threshold not in methods:
                rhe.fatal(
                    f"Threshold must be a number or {methods} "
                    f"while it is {self.intensity_threshold}"
                )
            if self.intensity_threshold == "auto":
                threshold = self.get_removed_rois_mean_value(
                    np_image, self.removed_mask
                )
            if self.intensity_threshold == "gafita2019":
                threshold = self.get_gafita2019_threshold(
                    itk_image, self.population_mean_liver
                )

        # threshold the mask
        self.verbose and print(f"Thresholding with {threshold}")
        np_mask[np_image < threshold] = 0

        return np_mask

    def get_removed_rois_mean_value(self, np_image, removed_mask):
        v_sum = np.sum(np_image[removed_mask == 1])
        n = np.sum(removed_mask == 1)
        return v_sum / n

    def get_gafita2019_threshold(self, itk_image, population_mean_liver):
        if population_mean_liver is None:
            rhe.fatal(f"For gafita2019 method, population_mean_liver must be provided")
        population_mean_liver = float(population_mean_liver)
        # we assume one roi is the liver
        liver_roi = None
        for roi in self.rois_to_remove:
            if "liver" in roi["filename"]:
                liver_roi = roi
        if liver_roi is None:
            rhe.fatal(
                f"Cannot find liver ROI in {self.rois_to_remove_folder}, this is needed to compute Gafita threshold"
            )
        roi_list = [liver_roi]

        # get the mean intensity in the liver
        np_mask = np.ones_like(sitk.GetArrayViewFromImage(itk_image))
        liver_mask = tmtv_mask_remove_rois(
            itk_image, np_mask, roi_list, roi_folder=self.rois_to_remove_folder
        )
        np_image = sitk.GetArrayViewFromImage(itk_image)
        mean_liver = np_image[liver_mask == 1].mean()
        std_liver = np_image[liver_mask == 1].std()
        self.verbose and print(
            f"Computed mean/std liver: {mean_liver} {std_liver}, population mean: {population_mean_liver=}"
        )

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
    print(f"Number of labels = {stats.GetNumberOfLabels()}")

    # Keep only labels with more than a given size
    volume = tmtv_mask.voxel_volume_cc
    max_size = int(min_size_cm3 / volume)
    print(f"{min_size_cm3=} -> {max_size=} pixels")
    foci = sitk.RelabelComponent(foci, minimumObjectSize=max_size)

    # relabel
    # (not needed for the final version)
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(foci)
    print(f"Number of labels = {stats.GetNumberOfLabels()}")

    # keep labels only if max intensity
    spect = tmtv.image
    spect_arr = sitk.GetArrayViewFromImage(spect)
    foci_arr = sitk.GetArrayFromImage(foci)
    total_max_intensity = np.max(spect_arr)
    print(f"{total_max_intensity=}")

    # Keep only labels where the maximum intensity exceeds the threshold
    for l in stats.GetLabels():
        # select pixels at the label
        label_arr = spect_arr[foci_arr == l]
        # print(f'{len(label_arr)=}')
        max_intensity = np.max(label_arr)
        # Check if the maximum intensity exceeds the threshold
        if max_intensity <= (percentage_threshold * total_max_intensity):
            foci_arr[foci_arr == l] = 0
            print(
                f"remove {l} {max_intensity=} vs {total_max_intensity}  --->   {max_intensity / total_max_intensity}"
            )

    # Keep only the labels to be retained
    a = sitk.GetImageFromArray(foci_arr)
    a.CopyInformation(foci)
    foci = a

    # relabel
    # (not needed for the final version)
    stats = sitk.LabelShapeStatisticsImageFilter()
    stats.Execute(foci)
    print(f"Number of labels = {stats.GetNumberOfLabels()}")

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
