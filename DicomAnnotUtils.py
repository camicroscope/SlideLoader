import json
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom import Sequence
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
import numpy as np
from copy import deepcopy
import random
from datetime import datetime

import argparse

featureTemplate = {
    "type": "Feature",
    "properties": {
        "style": {
            "color":"#fc7e00",
            "lineJoin":"round",
            "lineCap":"round",
            "isFill":True
        }
    },
    "geometry" : {
        "type":"Polygon",
        
        "coordinates" : []
    },
    "bound":{
        "type":"Polygon",
        "coordinates" : []
    }
}

annotTemplate = {
    "creator": "dicomImport",
    "provenance": {
        "image": {
            "slide": "ADD_CAMIC_SLIDE_ID",
            "dicom-ReferencedSOPClassUID": "",
            "dicom-ReferencedSOPInstanceUID": "",
            "dicom-study": "",
            "dicom-series": "",
            "dicom-instance": "",
        },
        "analysis": {
            "source": "human", # may not be true!
            "execution_id": "dicom-?",
            "name": "imported dicom annotation"
        }
    },
    "properties": {
        "annotations":{
            "name":"imported dicom annotation",
            "notes":""
        }
    },
    "geometries": {
        "type" : "FeatureCollection",
        "features" : []
    }
}

def _generate_random_string(n):
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return ''.join(random.choice(letters) for _ in range(n))

def get_dicom_info(image_path):
    # Read the DICOM file
    ds = pydicom.dcmread(image_path)
    
    # Extract DICOM attributes
    patient_id = ds.get('PatientID', 'Unknown')
    study_instance_uid = ds.get('StudyInstanceUID', 'Unknown')
    series_instance_uid = ds.get('SeriesInstanceUID', 'Unknown')
    image_width = int(ds.get('TotalPixelMatrixColumns', 0))
    image_height = int(ds.get('TotalPixelMatrixRows', 0))
    
    return {
        'PatientID': patient_id,
        'StudyInstanceUID': study_instance_uid,
        'SeriesInstanceUID': series_instance_uid,
        'ImageWidth': image_width,
        'ImageHeight': image_height
    }

def create_annotation_dicom(annot_arrays, slide_file, geojson):
    # the slide/ref dataset
    reference_ds = pydicom.dcmread(slide_file)
    # the annot dataset 
    ds = Dataset()
    # Copy file meta information

    attrs_to_copy = [
        'StudyID', 'PatientID', 'PatientName', 'PatientBirthDate', 'StudyInstanceUID', 'StudyDate', 'StudyTime', 'Modality', 'SeriesNumber',
        'PatientSex', 'ReferringPhysicianName', 'AccessionNumber', 'Manufacturer', 'ManufacturerModelName', 'DeviceSerialNumber', 'SoftwareVersions', 'InstanceNumber'
    ]
    for attr in attrs_to_copy:
        setattr(ds, attr, getattr(reference_ds, attr))

    # annotation fields
    # ds.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.91.1'
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.91.1'
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = generate_uid()
    ds.ContentLabel = str(geojson['properties']['annotations']['name']).upper()
    ds.ContentDescription = geojson['properties']['annotations']['notes']
    ds.AnnotationCoordinateType = "2D"
    ds.PixelOriginInterpretation = 'VOLUME'
    ds.Laterality = 'L'
    ds.Modality = "ANN"
    ds.StudyID = "S1"
    ds.SeriesNumber = "0"

    current_date = datetime.now().strftime('%Y%m%d')
    current_time = datetime.now().strftime('%H%M%S')
    # Set ContentDate and ContentTime attributes
    ds.ContentDate = current_date
    ds.ContentTime = current_time


    referenced_series_sequence = Dataset()
    referenced_instance_sequence = Dataset()
    referenced_instance_sequence.ReferencedSOPInstanceUID = reference_ds.SOPInstanceUID
    referenced_instance_sequence.ReferencedSOPClassUID = reference_ds.SOPClassUID
    referenced_series_sequence.ReferencedInstanceSequence = [referenced_instance_sequence]
    referenced_series_sequence.SeriesInstanceUID = reference_ds.SeriesInstanceUID
    ds.ReferencedSeriesSequence = [referenced_series_sequence]

    referenced_image_sequence = Dataset()
    referenced_image_sequence.ReferencedSOPClassUID = reference_ds.SOPClassUID
    referenced_image_sequence.ReferencedSOPInstanceUID = reference_ds.SOPInstanceUID
    ds.ReferencedImageSequence = [referenced_image_sequence]


    # add the annotation data
    ds.AnnotationGroupSequence = []
    i = 0
    idx = 1
    point_indices = []
    # make the array first?
    for points_array in annot_arrays:
        point_indices.append(idx)
        idx+=len(points_array)
    
    # now do the rest?
    for points_array in annot_arrays:
        
        # Create a new AnnotationGroupSequence item
        annotation_group_item = Dataset()
        annotation_group_item.PointCoordinatesData = points_array.tobytes()  # Convert numpy array to bytes
        annotation_group_item.LongPrimitivePointIndexList = np.array([1], dtype=np.int32).tobytes()

        #annotation_group_item.LongPrimitivePointIndexList = bytes(points_array)
        annotation_group_item.GraphicType = "POLYGON"
        annotation_property_seq = Sequence()
        item_dataset = Dataset()
        item_dataset.CodeValue = "91723000"
        item_dataset.CodingSchemeDesignator = "DCM"
        item_dataset.CodeMeaning = "Anatomical Stucture"
        annotation_property_seq.append(item_dataset)
        annotation_group_item.AnnotationPropertyTypeCodeSequence = annotation_property_seq
        annotation_group_item.AnnotationGroupNumber = i
        i+=1
        annotation_group_item.NumberOfAnnotations = 1
        annotation_group_item.AnnotationAppliesToAllOpticalPaths = "YES"
        annotation_group_item.AnnotationGroupUID = generate_uid()
        annotation_group_item.AnnotationGroupLabel = "Annotation Group Label" 
        annotation_group_item.AnnotationGroupGenerationType = "MANUAL"
        annotation_group_item.AnnotationPropertyCategoryCodeSequence = annotation_property_seq
        annotation_group_item.AnnotationPropertyCategoryCodeSequence = annotation_property_seq
        ds.AnnotationGroupSequence.append(annotation_group_item)
    # Create a DICOM File Meta Information header
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationVersionName = 'camic@0.0.1'
    # Set the File Meta Information header
    ds.file_meta = file_meta
    return ds

# camic to dicom 
def camicToDicom(annot_file, slide_file):
    dicom_data = get_dicom_info(slide_file)
    width = int(dicom_data['ImageWidth'])
    height = int(dicom_data['ImageHeight'])
    with open(annot_file, 'r') as f:
        annot_geo = json.load(f)
        annot_arrays = []
        for x in annot_geo:
            coordinates = x['geometries']['features'][0]['geometry']['coordinates'][0]
            flattened_coords = [[pair[0] * width, pair[1] * height] for pair in coordinates]
            converted_coords = np.array(flattened_coords, dtype=np.float32)
            annot_arrays.append(converted_coords)
        annot_ds = create_annotation_dicom(annot_arrays, slide_file, x)
        return annot_ds
        

def _makeBound(coords_mat):
    try:
        min_x = float(np.min(coords_mat[:, 0]))
        max_x = float(np.max(coords_mat[:, 0]))
        min_y = float(np.min(coords_mat[:, 1]))
        max_y = float(np.max(coords_mat[:, 1]))
        bound_coords = [[min_x, min_y], [min_x, max_y], [max_x, max_y], [max_x, min_y],[min_x, min_y]]
        return bound_coords
    except BaseException as e:
        print("coords mat")
        print(coords_mat)
        raise e

def _polygon_area(vertices):
    n = len(vertices)
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2

def _polygon_perimeter(vertices):
    perimeter = 0
    n = len(vertices)
    for i in range(n):
        j = (i + 1) % n
        perimeter += np.linalg.norm(np.array(vertices[i]) - np.array(vertices[j]))
    return perimeter

def getPointCoordinatesDataArray(x):
    if 'PointCoordinatesData' in x:
        n = x.PointCoordinatesData
        return np.frombuffer(n, dtype=np.float32)
    elif 'DoublePointCoordinatesData' in x:
        n = x.DoublePointCoordinatesData
        return np.frombuffer(n, dtype=np.float64)
    else:
        raise ValueError("No coordinates found in array item")


def convert_ellipse(x1_major,y1_major,x2_major,y2_major,x1_minor,y1_minor,x2_minor,y2_minor):    
    center_x = (x1_major + x2_major) / 2
    center_y = (y1_major + y2_major) / 2
    major_axis_length = np.sqrt((x2_major - x1_major)**2 + (y2_major - y1_major)**2) / 2
    minor_axis_length = np.sqrt((x2_minor - x1_minor)**2 + (y2_minor - y1_minor)**2) / 2
    rotation = np.arctan2(y2_major - y1_major, x2_major - x1_major)
    return center_x, center_y, major_axis_length, minor_axis_length, rotation

def dicomToCamic(annot_path, image_path, output_file, slide_id=None, file_mode=False):
    slide_ds = pydicom.dcmread(image_path)
    annot_ds = pydicom.dcmread(annot_path)
    slide_width = slide_ds.TotalPixelMatrixColumns
    slide_height = slide_ds.TotalPixelMatrixRows
    # get physical resolution 
    imaged_volume_width = slide_ds.ImagedVolumeWidth
    imaged_volume_height = slide_ds.ImagedVolumeHeight
    pixel_size_x = imaged_volume_width / slide_width
    pixel_size_y = imaged_volume_height / slide_height
    # millimeters to microns
    mpp_x = pixel_size_x * 1000
    #mpp_y = pixel_size_y * 1000
    # TODO this is just for POLYGON. generalize later.
    res = []
    for x in annot_ds.AnnotationGroupSequence:

        exported_annot = deepcopy(annotTemplate)
        exported_annot['properties']['annotations']['name'] = annot_ds.ContentLabel
        exported_annot['provenance']['analysis']['name'] = annot_ds.ContentLabel
        exported_annot['properties']['annotations']['notes'] = annot_ds.ContentDescription
        exported_annot['provenance']['analysis']['execution_id'] = "_DICOM_" + _generate_random_string(10)
        if slide_id:
            exported_annot['provenance']['image']['slide'] = slide_id
        exported_annot['provenance']['image']['dicom-ReferencedSOPClassUID'] = annot_ds.ReferencedImageSequence[0].ReferencedSOPClassUID
        exported_annot['provenance']['image']['dicom-ReferencedSOPInstanceUID'] = annot_ds.ReferencedImageSequence[0].ReferencedSOPInstanceUID
        exported_annot['provenance']['image']["dicom-study"] = annot_ds.StudyInstanceUID
        exported_annot['provenance']['image']["dicom-series"] = annot_ds.SeriesInstanceUID
        exported_annot['provenance']['image']["dicom-instance"] = annot_ds.SOPInstanceUID
        
        # handle other cases first
        if x.GraphicType == "ELLIPSE":
            m = getPointCoordinatesDataArray(x)
            # sets of 4 points, 8 numbers
            for i in range(8, len(m), 8):
                ellipse_points = m[i-8: i]
                x1_major = ellipse_points[0]/slide_width
                y1_major = ellipse_points[1]/slide_height
                x2_major = ellipse_points[2]/slide_width
                y2_major = ellipse_points[3]/slide_height
                x1_minor = ellipse_points[4]/slide_width
                y1_minor = ellipse_points[5]/slide_height
                x2_minor = ellipse_points[6]/slide_width
                y2_minor = ellipse_points[7]/slide_height
                center_x, center_y, major_axis_length, minor_axis_length, rotation = convert_ellipse(x1_major,y1_major,x2_major,y2_major,x1_minor,y1_minor,x2_minor,y2_minor)
                newFeature = deepcopy(featureTemplate)
                newFeature['geometry']['type'] = "Ellipse"
                newFeature['geometry']['coordinates'] = [center_x, center_y]
                newFeature['geometry']["radius"] = [major_axis_length,minor_axis_length],
                newFeature['geometry']["rotation"] = rotation
                newFeature['bound']['type'] = "Point"
                newFeature['bound']['coordinates'] = [center_x, center_y]
                exported_annot['geometries']['features'] = [newFeature]
                exported_annot['provenance']['analysis']['execution_id'] = "_DICOM_" + _generate_random_string(10)
                res.append(deepcopy(exported_annot))       
        elif x.GraphicType == "POINT":
            # sets of 1 point, 2 numbers
            m = getPointCoordinatesDataArray(x)
            # sets of 4 points, 8 numbers
            for i in range(2, len(m), 2):
                point = m[i-2: i]
                center_x = point[0]/slide_width
                center_y = point[1]/slide_height
                newFeature = deepcopy(featureTemplate)
                newFeature['geometry']['type'] = "Point"
                newFeature['geometry']['coordinates'] = [center_x, center_y]
                newFeature['bound']['type'] = "Point"
                newFeature['bound']['coordinates'] = [center_x, center_y]
                exported_annot['geometries']['features'] = [newFeature]
                exported_annot['provenance']['analysis']['execution_id'] = "_DICOM_" + _generate_random_string(10)
                res.append(deepcopy(exported_annot))  
        elif x.GraphicType == "RECTANGLE":
            m = getPointCoordinatesDataArray(x)
            # sets of 4 points, 8 numbers
            for i in range(8, len(m), 8):
                rect_points = m[i-8: i]
                x1 = rect_points[0]/slide_width
                y1 = rect_points[1]/slide_height
                x2 = rect_points[2]/slide_width
                y2 = rect_points[3]/slide_height
                x3 = rect_points[4]/slide_width
                y3 = rect_points[5]/slide_height
                x4 = rect_points[6]/slide_width
                y4 = rect_points[7]/slide_height
                newFeature = deepcopy(featureTemplate)
                newFeature['geometry']['type'] = "Polygon"
                newFeature['geometry']['coordinates'] = [[x1,y1], [x2,y2], [x3,y3], [x4,y4], [x1,y1]]
                newFeature['geometry']["radius"] = [major_axis_length,minor_axis_length],
                newFeature['geometry']["rotation"] = rotation
                newFeature['bound']['type'] = "Polygon"
                newFeature['bound']['coordinates'] = [[x1,y1], [x2,y2], [x3,y3], [x4,y4], [x1,y1]]
                exported_annot['geometries']['features'] = [newFeature]
                exported_annot['provenance']['analysis']['execution_id'] = "_DICOM_" + _generate_random_string(10)
                res.append(deepcopy(exported_annot))
        elif x.GraphicType == "POLYGON" or x.GraphicType == "POLYLINE":
            m = getPointCoordinatesDataArray(x)
            coordinates_array = (np.array(m).reshape(-1, 2)) / [slide_width,slide_height] # normalize coordinates for camicroscope
            # split into different geometry objects Index List
            indexList = np.frombuffer(x.LongPrimitivePointIndexList, dtype=np.int32)
            #print("IndexList", indexList)
            #print("len Index List", len(indexList))
            #print("coordinates_array shape", coordinates_array.shape)
            if len(indexList) > 1:
                # split
                prevIndex = 0
                for idx in indexList[1:]:
                    end_idx = int((idx-1)/2)
                    #print("prev", prevIndex, "idx", idx)
                    # make a thing 
                    points = coordinates_array[prevIndex:end_idx, :]
                    points = np.concatenate((points, [points[0]]))
                    #print('len(points)', len(points))
                    if len(points) > 0:
                        newFeature = deepcopy(featureTemplate)
                        newFeature['geometry']['coordinates'].append(points.tolist())
                        newFeature['bound']['coordinates'].append(_makeBound(points))
                        exported_annot['geometries']['features'] = [newFeature]
                        exported_annot['provenance']['analysis']['execution_id'] = "_DICOM_" + _generate_random_string(10)
                        res.append(deepcopy(exported_annot))
                    prevIndex = end_idx
                    # and the bound
                # then add the last one
                points = coordinates_array[prevIndex:, :]
                if len(points) > 0:
                    newFeature = deepcopy(featureTemplate)
                    newFeature['geometry']['coordinates'].append(points.tolist())
                    newFeature['bound']['coordinates'].append(_makeBound(points))
                    exported_annot['provenance']['analysis']['execution_id'] = "_DICOM_" + _generate_random_string(10)
                    exported_annot['geometries']['features'] = [newFeature]
                    res.append(deepcopy(exported_annot))
            else:
                # whole thing at once. Only do area and circumference here.
                points = coordinates_array
                newFeature = deepcopy(featureTemplate)
                newFeature['geometry']['coordinates'].append(points.tolist())
                newFeature['bound']['coordinates'].append(_makeBound(points))
                exported_annot['geometries']['features'] = [newFeature]
                area = _polygon_perimeter(points.tolist()) * mpp_x * slide_width
                perimeter = _polygon_area(points.tolist()) * (mpp_x * slide_width)**2
                exported_annot['properties']['annotations']['circumference'] = str(area)+ " μm"
                exported_annot['properties']['annotations']['area'] = str(perimeter) + " μm²"
                exported_annot['provenance']['analysis']['execution_id'] = "_DICOM_" + _generate_random_string(10)
                res.append(deepcopy(exported_annot))
    
    if file_mode:
        n = 0
        for x in res:
            n += 1
            output_fn = output_file + "_" + str(n) + ".json"
            with open(output_fn, 'w') as f:
                json.dump(x, f)
                print("saved to", output_fn)
    else:
        return res

# demonstration example
def demo():
    annot_file = './annots_camic.json'
    slide_file = '/Users/rbirmin/Documents/distro/images/5d8b1b52d0/e25e1997-b86a-42de-aa8c-83ca18444bf2.dcm'
    annot_ds = camicToDicom(annot_file, slide_file)
    annot_ds.save_as("test_out.dcm", write_like_original=False)
    print("now working backwards for test")
    annot_output = "./test_out.dcm"
    dicomToCamic(annot_output, slide_file, "test_out2", slide_id='65fc65851200600012eb9222', file_mode=True)
    exit(0)

if __name__ == "__main__":
    demo()
    # Create argument parser
    parser = argparse.ArgumentParser(description='Convert annotations between CAMIC and DICOM')

    # Add arguments
    parser.add_argument('operation', choices=['import', 'export'], help='Operation to perform (camic_to_dicom or dicom_to_camic)')
    parser.add_argument('annot_file', help='Path to the annotation file (json or dcm)')
    parser.add_argument('slide_file', help='Path to the slide file (dcm)')
    parser.add_argument('output_file', help='Path to the output file (dcm or json)')
    parser.add_argument('--slide_id', help='Slide ID (optional)')
    

    # Parse arguments
    args = parser.parse_args()
    slide_id = "ADD_CAMIC_SLIDE_ID_HERE" # note: not literally here, but if you don't give a slide id, you should add it eventually to the output
    if args.slide_id:
        slide_id = args.slide_id

    # Perform the selected operation
    if args.operation == 'export':
        annot_ds = camicToDicom(args.annot_file, args.slide_file)
        annot_ds.save_as(args.output_file, write_like_original=False)
    elif args.operation == 'import':
        dicomToCamic(args.annot_file, args.slide_file, args.output_file, slide_id=slide_id, file_mode=True)
    else:
        print("Invalid operation. Choose 'export' (camic_to_dicom) or 'import' (dicom_to_camic)")
