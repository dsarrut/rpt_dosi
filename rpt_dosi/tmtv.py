import SimpleITK as sitk
import numpy as np
import rpt_dosi.images as rim


def dilate_mask(img, dilatation_mm):
    # convert radius in vox
    radius = [int(round(dilatation_mm / img.GetSpacing()[0])),
              int(round(dilatation_mm / img.GetSpacing()[1])),
              int(round(dilatation_mm / img.GetSpacing()[2]))]
    # Set the kernel element
    dilate_filter = sitk.BinaryDilateImageFilter()
    dilate_filter.SetKernelRadius(radius)
    dilate_filter.SetKernelType(sitk.sitkBall)
    dilate_filter.SetForegroundValue(1)
    output = dilate_filter.Execute(img)
    return output


def tmtv_mask_cut_the_head(image, mask, skull_filename, margin_mm):
    roi = sitk.ReadImage(skull_filename)
    roi_img = rim.resample_itk_image_like(roi, image, 0, linear=False)
    roi_arr = sitk.GetArrayFromImage(roi_img)
    indices = np.argwhere(roi_arr == 1)
    most_inferior_pixel = indices[np.argmin(indices[:, 0])]
    margin_pix = int(round(margin_mm / image.GetSpacing()[0]))
    most_inferior_pixel[0] -= margin_pix
    mask[most_inferior_pixel[0]:-1, :, :] = 0


def tmtv_apply_mask(image, mask):
    # convert img in nparray
    img_np = sitk.GetArrayFromImage(image)

    # apply the mask
    img_np[mask == 0] = 0

    # back to itk images
    img = sitk.GetImageFromArray(img_np)
    img.CopyInformation(image)
    return img


def tmtv_mask_threshold(image, mask, threshold):
    # convert img in nparray
    img_np = sitk.GetArrayFromImage(image)

    # threshold the mask
    mask[img_np < threshold] = 0


def tmtv_mask_remove_rois(image, mask, roi_list):
    mean_value = 0
    n = 0
    img_np = sitk.GetArrayViewFromImage(image)
    # loop on the roi
    for roi in roi_list:
        # read image
        roi_img = sitk.ReadImage(roi['filename'])
        # check size and resample if needed
        roi_img = rim.resample_itk_image_like(roi_img, image, 0, linear=False)
        # dilatation ?
        roi_img = dilate_mask(roi_img, roi['dilatation'])
        # update the mask
        roi_np = sitk.GetArrayViewFromImage(roi_img)
        mask[roi_np == 1] = 0
        # mean value in the roi
        v = img_np[roi_np == 1]
        mean_value += np.sum(v)
        n += len(v)
    mean_value /= n
    return mean_value


def tmtv_compute_mask(image, skull_filename, head_margin_mm, roi_list, threshold, verbose=False):
    # initialize the mask
    mask = np.ones_like(sitk.GetArrayViewFromImage(image))

    # cut the head
    verbose and print(f'Cut the head with {head_margin_mm}mm margin')
    tmtv_mask_cut_the_head(image, mask, skull_filename, margin_mm=head_margin_mm)

    # remove the rois
    verbose and print(f'Remove the {len(roi_list)} ROIs')
    mean_value = tmtv_mask_remove_rois(image, mask, roi_list)

    # threshold
    if threshold == 'auto':
        threshold = mean_value
    else:
        threshold = float(threshold)
    verbose and print(f'Thresholding with {threshold}')
    tmtv_mask_threshold(image, mask, threshold)

    # apply the mask
    tmtv = tmtv_apply_mask(image, mask)

    # convert mask to itk image
    mask = sitk.GetImageFromArray(mask)
    mask.CopyInformation(image)

    return tmtv, mask


def find_foci(tmtv, tmtv_mask, min_size_cm3=1, percentage_threshold=0.001):
    # get the sitk image
    mask = tmtv_mask.image

    # convert mask image into char
    mask = sitk.Cast(mask, sitk.sitkInt8)

    # pre processing, image closing
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
    volume = tmtv_mask.voxel_volume_ml
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
