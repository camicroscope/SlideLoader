import image_reader
import dev_utils
import ome_types
from file_extensions import BIOFORMATS_EXTENSIONS
import BFBridge.python as bfbridge


jvm = bfbridge.BFBridgeVM()

class BioFormatsReader(image_reader.ImageReader):
    @staticmethod
    def reader_name():
        return "bioformats"

    @staticmethod
    def extensions_set():
        return BIOFORMATS_EXTENSIONS

    def __init__(self, imagepath):
        if not hasattr(dev_utils.keep_alive_for_thread, "bfthread"):
            dev_utils.keep_alive_for_thread.bfthread = bfbridge.BFBridgeThread(jvm)

        # Conventionally internal attributes start with underscore.
        # When using them without underscore, there's the risk that
        # a property has the same name as a/the getter, which breaks
        # the abstract class. Hence all internal attributes start with underscore.
        self._bfreader = bfbridge.BFBridgeInstance(dev_utils.keep_alive_for_thread.bfthread)
        if self._bfreader is None:
            raise RuntimeError("cannot make bioformats instance")
        self._image_path = imagepath
        code = self._bfreader.open(imagepath)
        if code < 0:
            raise IOError("Could not open file " + imagepath + ": " + self._bfreader.get_error_string())
        # Note: actually stores the format, not the vendor ("Hamamatsu NDPI" instead of "Hamamatsu")
        self._vendor = self._bfreader.get_format()
        self._level_count = self._bfreader.get_resolution_count()
        self._dimensions = (self._bfreader.get_size_x(), self._bfreader.get_size_y())
        self._level_dimensions = [self._dimensions]
        for l in range(1, self._level_count):
            self._bfreader.set_current_resolution(l)
            self._level_dimensions.append( \
                (self._bfreader.get_size_x(), self._bfreader.get_size_y()))

    @property
    def level_count(self):
        return self._level_count

    @property
    def dimensions(self):
        return self._dimensions

    @property
    def level_dimensions(self):
        return self._level_dimensions

    @property
    def associated_images(self):
        return None

    def read_region(self, location, level, size):
        self._bfreader.set_current_resolution(level)
        return self._bfreader.open_bytes_pil_image(0, \
            location[0], location[1], size[0], size[1])

    def get_thumbnail(self, max_size):
        return self._bfreader.open_thumb_bytes_pil_image(0, max_size[0], max_size[1])

    def get_basic_metadata(self, extended):
        metadata = {}

        try:
            ome_xml_raw = self._bfreader.dump_ome_xml_metadata()
        except BaseException as e:
            raise OverflowError("XML metadata too large for file considering the preallocated buffer length. " + str(e))
        try:
            ome_xml = ome_types.from_xml(ome_xml_raw)
        except BaseException as e:
            raise RuntimeError("get_basic_metadata: OME-XML parsing of metadata failed, error: " + \
                str(e) + " when parsing: " + ome_xml_raw)

        # https://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2016-06/ome_xsd.html
        # https://bio-formats.readthedocs.io/en/latest/metadata-summary.html

        if extended:
            return {"ome-xml": ome_xml_raw}

        metadata['width'] = str(self._dimensions[0])
        metadata['height'] = str(self._dimensions[1])
        try:
            metadata['mpp-x'] = str(ome_xml.images[0].pixels.physical_size_x)
            metadata['mpp-y'] = str(ome_xml.images[0].pixels.physical_size_y)
        except:
            metadata['mpp-x'] = "0"
            metadata['mpp-y'] = "0"
        metadata['vendor'] = self._vendor
        metadata['level_count'] = int(self._level_count)
        try:
            metadata['objective'] = ome_xml.instruments[0].objectives[0].nominal_magnification
        except:
            try:
                metadata['objective'] = ome_xml.instruments[0].objectives[0].calibrated_magnification
            except:
                metadata['objective'] = -1.0

        metadata['comment'] = ""
        metadata['study'] = ""
        metadata['specimen'] = ""
        metadata['md5sum'] = dev_utils.file_md5(self._image_path)

        return metadata
