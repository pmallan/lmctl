from abc import ABC, abstractmethod
import json
import yaml
from tabulate import tabulate

TABLE_FORMAT = 'table'
YAML_FORMAT = 'yaml'
JSON_FORMAT = 'json'


def determine_format_class(output_format):
    if output_format == TABLE_FORMAT:
        result = TableFormat
    elif output_format == YAML_FORMAT:
        result = YamlFormat
    elif output_format == JSON_FORMAT:
        result = JsonFormat
    else:
        click.echo('Format {0} is not a valid option'.format(output_format), err=True)
        exit(1)
    return result


class Format(ABC):

    @abstractmethod
    def convert_list(self, element_list):
        pass


class JsonFormat(Format):

    def convert_list(self, element_list):
        data = {'items': element_list}
        return json.dumps(data)


class YamlFormat(Format):

    def convert_list(self, element_list):
        data = {'items': element_list}
        return yaml.dump(data)


class TableFormat(Format):

    def __init__(self, headers, row_processor):
        self.headers = headers
        self.row_processor = row_processor

    def convert_list(self, element_list):
        table_data = []
        for element in element_list:
            table_data.append(self.__element_to_table_row(element))
        return tabulate(table_data, headers=self.headers, tablefmt='orgtbl')

    def __element_to_table_row(self, element):
        table_row = self.row_processor(element)
        if table_row is None:
            table_row = []
        return table_row