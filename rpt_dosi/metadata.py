import json
from rpt_dosi.utils import fatal, warning
import rpt_dosi.utils as he
from typing import Dict
import os


class ClassWithMetaData:
    """
    Class to manage metadata, providing methods to convert to/from dict and JSON.
    The class fields that are considered as metadata are store in _metadata_fields.
    """

    # List of attribute names to be considered as metadata
    _metadata_fields: Dict[str, type] = {}

    def __init__(self):
        self._debug_eq = False
        self._instance_metadata_fields: Dict[str, type] = {}
        self._info_width = 30

    def to_dict(self):
        """
        Store the metadata attributes to a dictionary.
        """
        all_fields = self._metadata_fields | self._instance_metadata_fields
        metadata_dict = {}
        for attr_name, attr_type in all_fields.items():
            metadata_dict[attr_name] = getattr(self, attr_name)
        return metadata_dict

    def from_dict(self, data):
        """
        Set the metadata attributes of the instance from a dictionary.
        """
        for attr_name in self._metadata_fields.keys():
            if attr_name in data:
                value = data[attr_name]
                self.set_metadata(attr_name, value)
        for attr_name in data:
            if attr_name in self._metadata_fields.keys():
                continue
            value = data[attr_name]
            mtype = type(value)
            self.add_metadata_field(attr_name, mtype)
            self.set_metadata(attr_name, value)

    def save_to_json(self, filepath):
        """
        Save the metadata attributes to a JSON file.
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=4)
        except Exception as e:
            fatal(f"Unexpected Error while writing {filepath}: {e}")

    def load_from_json(self, filepath):
        """
        Load metadata attributes from a JSON file.
        """
        if os.path.getsize(filepath) == 0:
            os.remove(filepath)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.from_dict(data)
        except ValueError as e:
            fatal(f"Invalid JSON file: {filepath} {e}")
        except Exception as e:
            fatal(f"Unexpected Error while reading {filepath}: {e}")

    def add_metadata_field(self, key, mtype):
        all_fields = self._metadata_fields | self._instance_metadata_fields
        if key in all_fields.keys():
            return  # fatal(f'Cannot add the metadata field {key}, it already exists')
        self._instance_metadata_fields[key] = mtype

    def set_metadata(self, key, value):
        all_fields = self._metadata_fields | self._instance_metadata_fields
        if key not in all_fields.keys():
            fatal(f"No such metadata tag '{key}' in {all_fields.keys}")
        attr_type = all_fields[key]
        try:
            if value is None:
                setattr(self, key, value)
            else:
                setattr(self, key, attr_type(value))
        except ValueError:
            fatal(f"Tag {key} = {value} cannot be set to value {value}")

    def info(self):
        # Print all metadata, one per line keys and value
        s = ''
        metadata = self.to_dict()
        for name in metadata.keys():
            s += f'{name:<{self._info_width}}: {metadata[name]}\n'
        return s

    def __str__(self):
        # print metadata value only
        s = ''
        metadata = self.to_dict()
        for name in metadata.keys():
            v = metadata[name]
            # s += f'{name}={v} '
            s += f'{v}  '
        return s

    def debug_eq(self, s):
        if self._debug_eq is None:
            return
        print(he.colored.stylize(s, he.color_error))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        for key in self._metadata_fields.keys():
            if key not in other._metadata_fields.keys():
                self.debug_eq(f'{key} is not in {other._metadata_fields}')
                return False
            if getattr(self, key) != getattr(other, key):
                self.debug_eq(f'{key}={getattr(self, key)} is different from {getattr(other, key)}')
                return False
        for key in other._metadata_fields.keys():
            if key not in self._metadata_fields.keys():
                self.debug_eq(f'{key} is not in {self._metadata_fields}')
                return False
        return True


def sync_field_image_db(image, element_db, tag_name, sync_policy="auto"):
    if sync_policy == "auto":
        return sync_field_image_db_auto(image, element_db, tag_name)
    if sync_policy == "image_to_db":
        return sync_field_image_to_db(image, element_db, tag_name)
    if sync_policy == "db_to_image":
        return sync_field_db_to_image(image, element_db, tag_name)
    fatal(f"Unexpected value for sync_policy: {sync_policy}, "
          f"expected 'auto' or 'image_to_db' or 'db_to_image'")


def sync_field_image_to_db(image, element_db, tag_name):
    # check is key exist ?
    try:
        getattr(image, tag_name)
    except:
        setattr(image, tag_name, None)
    # set the image value to the db
    setattr(element_db, tag_name, getattr(image, tag_name))


def sync_field_db_to_image(image, element_db, tag_name):
    # check is key exist ?
    try:
        getattr(element_db, tag_name)
    except:
        setattr(element_db, tag_name, None)
    # set the db value to the image
    setattr(image, tag_name, getattr(element_db, tag_name))


def sync_field_image_db_auto(image, element_db, tag_name):
    # check is key exist ? If not, set it to None
    try:
        getattr(element_db, tag_name)
    except:
        setattr(element_db, tag_name, None)
    try:
        getattr(image, tag_name)
    except:
        setattr(image, tag_name, None)
    # do nothing if the value is the same
    if getattr(element_db, tag_name) == getattr(image, tag_name):
        return
    # set it if one is None
    if getattr(image, tag_name) is None:
        setattr(image, tag_name, getattr(element_db, tag_name))
        return
    if getattr(element_db, tag_name) is None:
        setattr(element_db, tag_name, getattr(image, tag_name))
        return
    # warning : two different values
    warning(f'Warning: different {tag_name}, db = {getattr(element_db, tag_name)} '
            f'while image = {getattr(image, tag_name)} ({image.filename})')


def sync_field_image_db_check(image, element_db, tag_name, ok=True, msg=''):
    try:
        getattr(element_db, tag_name)
    except:
        msg += f'{tag_name} does not exist in {element_db}/n'
        return False, msg
    try:
        getattr(image, tag_name)
    except:
        msg += f'{tag_name} does not exist in {image}\n'
        return False, msg
    # do nothing if the value is the same
    v_db = getattr(element_db, tag_name)
    v_im = getattr(image, tag_name)
    if v_db == v_im:
        return ok, msg
    msg += f'Different {tag_name}: db="{v_db}" vs image="{v_im}"'
    return False, msg
