import gzip
import lzma
import json

# Package imports
from target.logger import get_logger

LOGGER = get_logger()


def config_compression(config_default):
    config = {
        'file_type': 'jsonl',
        'compression': 'none'
    }
    config.update(config_default)

    if f"{config.get('compression')}".lower() == 'gzip':
        config['open_func'] = gzip.open
        config['naming_convention_default'] = config['naming_convention_default'] + '.gz'
        config['naming_convention'] = config['naming_convention'] + '.gz'

    elif f"{config.get('compression')}".lower() == 'lzma':
        config['open_func'] = lzma.open
        config['naming_convention_default'] = config['naming_convention_default'] + '.xz'
        config['naming_convention'] = config['naming_convention'] + '.xz'

    elif f"{config.get('compression')}".lower() in {'', 'none'}:
        config['open_func'] = open

    else:
        raise NotImplementedError(
            "Compression type '{}' is not supported. "
            "Expected: 'none', 'gzip', or 'lzma'"
            .format(f"{config.get('compression')}".lower()))

    return config


def save_file(file_data, config):
    if any(file_data['file_data']):
        with config.get('open_func')(file_data['file_name'], 'at', encoding='utf-8') as output_file:
            output_file.writelines((json.dumps(record) + '\n' for record in file_data['file_data']))

        del file_data['file_data'][:]
        LOGGER.debug("'{}' file saved using open_func '{}'".format(file_data['file_name'], config.get('open_func').__name__))
