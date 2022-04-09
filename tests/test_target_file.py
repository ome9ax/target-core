'''Tests for the target.main module'''
# Standard library imports

from target.file import gzip, lzma, json, config_compression, save_file
from tests.test_target import Path, raises, deepcopy, get_config, clear_dir, config, file_metadata

# NOTE: hack to please the lint
config = config
file_metadata = file_metadata


def test_config_compression(config):
    '''TEST : extract and enrich the configuration'''

    assert config_compression(get_config(str(Path('tests', 'resources', 'config_naked.json')))) == {
        'file_type': 'jsonl',
        'compression': 'none',
        'naming_convention': '{stream}-{timestamp:%Y%m%dT%H%M%S}.json',
        'memory_buffer': 64e6,
        'naming_convention_default': '{stream}-{timestamp:%Y%m%dT%H%M%S}.json',
        'open_func': open
    }

    assert config_compression(get_config(str(Path('tests', 'resources', 'config_compression_gzip.json')))) == {
        'file_type': 'jsonl',
        'compression': 'gzip',
        'naming_convention': '{stream}-{timestamp:%Y%m%dT%H%M%S}.json.gz',
        'memory_buffer': 64e6,
        'naming_convention_default': '{stream}-{timestamp:%Y%m%dT%H%M%S}.json.gz',
        'open_func': gzip.open
    }

    assert config_compression(get_config(str(Path('tests', 'resources', 'config_compression_lzma.json')))) == {
        'file_type': 'jsonl',
        'compression': 'lzma',
        'naming_convention': '{stream}-{timestamp:%Y%m%dT%H%M%S}.json.xz',
        'memory_buffer': 64e6,
        'naming_convention_default': '{stream}-{timestamp:%Y%m%dT%H%M%S}.json.xz',
        'open_func': lzma.open
    }

    with raises(NotImplementedError):
        config_compression(get_config(str(Path('tests', 'resources', 'config_compression_dummy.json'))))


def test_save_file(config, file_metadata):
    '''TEST : simple save_file call'''
    Path(config['temp_dir']).mkdir(parents=True, exist_ok=True)

    # NOTE: test compression saved file
    for open_func, extension in {open: '', gzip.open: '.gz', lzma.open: '.xz'}.items():
        file_metadata_copy = deepcopy(file_metadata)
        for _, file_info in file_metadata_copy.items():
            file_info['file_name'] = file_info['file_name'].parent / f"{file_info['file_name'].name}{extension}"
            save_file(file_info, {'open_func': open_func})

        assert not file_metadata_copy['tap_dummy_test-test_table_one']['file_name'].exists()
        assert not file_metadata_copy['tap_dummy_test-test_table_two']['file_name'].exists()
        assert file_metadata_copy['tap_dummy_test-test_table_three']['file_name'].exists()

        with open_func(file_metadata_copy['tap_dummy_test-test_table_three']['file_name'], 'rt', encoding='utf-8') as input_file:
            assert [item for item in input_file] == [json.dumps(item) + '\n' for item in file_metadata['tap_dummy_test-test_table_three']['file_data']]

        del file_metadata_copy

    clear_dir(Path(config['temp_dir']))
