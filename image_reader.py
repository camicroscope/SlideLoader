# Please note: if you would like to import a specific reader,
# you should "import image_reader" first to avoid a cyclic dependency error

from abc import ABCMeta, abstractmethod

# Allow near drop-in replacements for OpenSlide-Python
class ImageReader(metaclass=ABCMeta):
    # currently: "openslide", "bioformats"
    @staticmethod
    @abstractmethod
    def reader_name():
        pass

    @staticmethod
    @abstractmethod
    def extensions_set():
        pass

    # Raises exception on error
    @abstractmethod
    def __init__(self):
        pass

    @property
    @abstractmethod
    def level_count(self):
        pass

    @property
    @abstractmethod
    def dimensions(self):
        pass

    @property
    @abstractmethod
    def level_dimensions(self):
        pass

    @abstractmethod
    def associated_images(self):
        pass

    @abstractmethod
    def read_region(self, location, level, size):
        pass

    @abstractmethod
    def get_thumbnail(self, max_size):
        pass

    # raises exception
    @abstractmethod
    def get_basic_metadata(self, extended):
        pass

from OpenSlideReader import OpenSlideReader
from BioFormatsReader import BioFormatsReader

# Decreasing order of performance
readers = [OpenSlideReader, BioFormatsReader]


# Replaces the constructor of the abstract class
# Usage:
# image = ImageReader.construct_reader("/file/path")
# Returns a reader
# Otherwise raises an object with attribute "error"
def construct_reader(imagepath):
    relevant_readers = []
    extension = imagepath.split(".")[-1].lower()

    for r in readers:
        if extension in r.extensions_set():
            relevant_readers.append(r)
    if len(relevant_readers) == 0:
        raise RuntimeError({"error": "File extension unsupported, no readers are compatible"})

    reader_names = []
    reader = None
    errors = []
    for r in relevant_readers:
        try:
            reader = r(imagepath)
            break
        except Exception as e:
            reader_names.append(r.reader_name())
            errors.append(r.reader_name() + ": " + str(e))
            continue
    if reader is None:
        raise RuntimeError({"type": ",".join(reader_names), "error": ", ".join(errors)})
    return reader


from pydicom import dcmread
import base64
dicom_extensions = set(["dcm", "dic", "dicom"])

# For file formats where multiple files are opened together,
# we should move them to a directory. This function infers a common name.
def suggest_folder_name(filepath, extension):
    try:
        if extension in dicom_extensions:
            ds = dcmread(filepath)
            #study_instance_uid = ds[0x0020,0x000D].repval
            series_instance_uid = ds[0x0020,0x000E].repval
            #uid = study_instance_uid + ".." + series_instance_uid
            uid = series_instance_uid
            summary = 0

            for c in uid:
                if c == '.':
                    c = 10
                else:
                    c = int(c)
                summary *= 11
                summary += c

            # make it a byte array
            summary = hex(summary)[2:]
            if len(summary) % 2 == 1:
                summary = '0' + summary
            summary = bytes.fromhex(summary)
            summary = base64.urlsafe_b64encode(summary).decode("ascii").replace("=", "")
            return summary
        return ""
    except:
        return ""
