import json
from rpt_dosi.helpers import fatal
from typing import Dict


class ClassWithMetaData:
    """
    Class to manage metadata, providing methods to convert to/from dict and JSON.
    The class fields that are considered as metadata are store in _metadata_fields.
    """

    # List of attribute names to be considered as metadata
    _metadata_fields: Dict[str, type] = {}

    def to_dict(self):
        """
        Store the metadata attributes to a dictionary.
        """
        metadata_dict = {}
        for attr_name, attr_type in self._metadata_fields.items():
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
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.from_dict(data)
        except ValueError as e:
            fatal(f"Invalid JSON file: {filepath} {e}")
        except Exception as e:
            fatal(f"Unexpected Error while reading {filepath}: {e}")

    def set_metadata(self, key, value):
        if key not in self._metadata_fields:
            fatal(f"No such metadata tag '{key}' in {self._metadata_fields}")
        attr_type = self._metadata_fields[key]
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
            s += f'{name}: {metadata[name]}\n'
        return s

    def __str__(self):
        # print metadata value only
        s = ''
        metadata = self.to_dict()
        for name in metadata.keys():
            v = metadata[name]
            s += f'{v} '
        return s
