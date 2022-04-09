#!/usr/bin/env python3

__version__ = '0.0.0'

import argparse
import json
from pathlib import Path
import sys
import tempfile
import datetime

from jsonschema import Draft4Validator, FormatChecker
from decimal import Decimal

from target.file import config_compression, save_file

from target.logger import get_logger
LOGGER = get_logger()

CONFIG_PARAMS = {
    'add_metadata_columns',
    'naming_convention',
    'timezone_offset',
    'memory_buffer',
    'temp_dir',
    'compression',
    'file_type'
}


def add_metadata_columns_to_schema(schema_message):
    '''Metadata _sdc columns according to the stitch documentation at
    https://www.stitchdata.com/docs/data-structure/integration-schemas#sdc-columns

    Metadata columns gives information about data injections
    '''
    schema_message['schema']['properties'].update(
        _sdc_batched_at={'type': ['null', 'string'], 'format': 'date-time'},
        _sdc_deleted_at={'type': ['null', 'string']},
        _sdc_extracted_at={'type': ['null', 'string'], 'format': 'date-time'},
        _sdc_primary_key={'type': ['null', 'string']},
        _sdc_received_at={'type': ['null', 'string'], 'format': 'date-time'},
        _sdc_sequence={'type': ['integer']},
        _sdc_table_version={'type': ['null', 'string']})

    return schema_message


def add_metadata_values_to_record(record_message, schema_message, timestamp):
    '''Populate metadata _sdc columns from incoming record message
    The location of the required attributes are fixed in the stream
    '''
    utcnow = timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    record_message['record'].update(
        _sdc_batched_at=utcnow,
        _sdc_deleted_at=record_message.get('record', {}).get('_sdc_deleted_at'),
        _sdc_extracted_at=record_message.get('time_extracted'),
        _sdc_primary_key=schema_message.get('key_properties'),
        _sdc_received_at=utcnow,
        _sdc_sequence=int(timestamp.timestamp() * 1e3),
        _sdc_table_version=record_message.get('version'))

    return record_message['record']


def remove_metadata_values_from_record(record_message):
    '''Removes every metadata _sdc column from a given record message
    '''
    for key in {
        '_sdc_batched_at',
        '_sdc_deleted_at',
        '_sdc_extracted_at',
        '_sdc_primary_key',
        '_sdc_received_at',
        '_sdc_sequence',
        '_sdc_table_version'
    }:

        record_message['record'].pop(key, None)

    return record_message['record']


def emit_state(state):
    if state is not None:
        line = json.dumps(state)
        LOGGER.debug('Emitting state {}'.format(line))
        sys.stdout.write('{}\n'.format(line))
        sys.stdout.flush()


def float_to_decimal(value):
    '''Walk the given data structure and turn all instances of float into
    double.'''
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [float_to_decimal(child) for child in value]
    if isinstance(value, dict):
        return {k: float_to_decimal(v) for k, v in value.items()}
    return value


def get_target_key(stream, config, timestamp=None):
    '''Creates and returns an S3 key for the stream'''

    # NOTE: Replace dynamic tokens
    key = config.get('naming_convention').format(stream=stream, timestamp=timestamp, date=timestamp)

    prefix = config.get('key_prefix', '')
    return str(Path(key).parent / f'{prefix}{Path(key).name}') if prefix else key


def persist_lines(messages, config, save_records=save_file):
    state = None
    schemas = {}
    key_properties = {}
    validators = {}
    file_data = {}

    timezone = datetime.timezone(datetime.timedelta(hours=config.get('timezone_offset'))) if config.get('timezone_offset') is not None else None

    # NOTE: Use the system specific temp directory if no custom temp_dir provided
    temp_dir = Path(config.get('temp_dir', tempfile.gettempdir())).expanduser()

    # NOTE: Create temp_dir if not exists
    temp_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now(timezone)

    for line in messages:
        try:
            m = json.loads(line)
        except json.decoder.JSONDecodeError:
            LOGGER.error(f'Unable to parse:\n{line}')
            raise
        message_type = m['type']
        if message_type == 'RECORD':
            if 'stream' not in m:
                raise Exception(f"Line is missing required key 'stream': {line}")
            stream = m['stream']

            if stream not in schemas:
                raise Exception(f'A record for stream {stream} was encountered before a corresponding schema')

            record_to_load = m['record']

            # NOTE: Validate record
            validators[stream].validate(float_to_decimal(record_to_load))

            record_to_load = add_metadata_values_to_record(m, {}, now) if config.get('add_metadata_columns') else remove_metadata_values_from_record(m)
            file_data[stream]['file_data'].append(record_to_load)

            # NOTE: write the lines into the temporary file when received data over 64Mb default memory buffer
            if sys.getsizeof(file_data[stream]['file_data']) > config.get('memory_buffer'):
                save_records(file_data[stream], config)

            state = None

        elif message_type == 'STATE':
            LOGGER.debug('Setting state to {}'.format(m['value']))
            state = m['value']

        elif message_type == 'SCHEMA':
            if 'stream' not in m:
                raise Exception("Line is missing required key 'stream': {}".format(line))
            stream = m['stream']

            schemas[stream] = add_metadata_columns_to_schema(m) if config.get('add_metadata_columns') else float_to_decimal(m['schema'])

            # NOTE: prevent exception *** jsonschema.exceptions.UnknownType: Unknown type 'SCHEMA' for validator.
            #       'type' is a key word for jsonschema validator which is different from `{'type': 'SCHEMA'}` as the message type.
            schemas[stream].pop('type')
            validators[stream] = Draft4Validator(schemas[stream], format_checker=FormatChecker())

            if 'key_properties' not in m:
                raise Exception('key_properties field is required')
            key_properties[stream] = m['key_properties']
            LOGGER.debug('Setting schema for {}'.format(stream))

            # NOTE: get the s3 file key. Persistent array data storage.
            if stream not in file_data:
                file_data[stream] = {
                    'target_key': get_target_key(
                        stream=stream,
                        config=config,
                        timestamp=now),
                    'file_name': temp_dir / config['naming_convention_default'].format(stream=stream, timestamp=now),
                    'file_data': []}

        elif message_type == 'ACTIVATE_VERSION':
            LOGGER.debug('ACTIVATE_VERSION {}'.format(line))

        else:
            LOGGER.warning('Unknown line type "{}" in line "{}"'.format(m['type'], m))

    for _, file_info in file_data.items():
        save_records(file_info, config)

    return state, file_data


def get_config(config_path):
    datetime_format = {
        'timestamp_format': '%Y%m%dT%H%M%S',
        'date_format': '%Y%m%d'
    }

    naming_convention_default = '{stream}-{timestamp}.json' \
        .replace('{timestamp}', '{timestamp:' + datetime_format['timestamp_format'] + '}') \
        .replace('{date}', '{date:' + datetime_format['date_format'] + '}')

    config = {
        'naming_convention': naming_convention_default,
        'memory_buffer': 64e6
    }

    with open(config_path) as input_file:
        config.update(json.load(input_file))

    config['naming_convention_default'] = naming_convention_default
    config['naming_convention'] = config['naming_convention'] \
        .replace('{timestamp}', '{timestamp:' + datetime_format['timestamp_format'] + '}') \
        .replace('{date}', '{date:' + datetime_format['date_format'] + '}')

    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Config file', required=True)
    args = parser.parse_args()

    state, file_data = persist_lines(
        sys.stdin,
        config_compression(get_config(args.config)))

    emit_state(state)
    LOGGER.debug('Exiting normally')


if __name__ == '__main__':  # pragma: no cover
    main()
