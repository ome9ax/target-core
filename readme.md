# target-core

![GitHub - License](https://img.shields.io/github/license/ome9ax/target-core)
[![Python package builder](https://github.com/ome9ax/target-core/workflows/Python%20package/badge.svg)](https://github.com/ome9ax/target-core)
[![codecov](https://codecov.io/gh/ome9ax/target-core/branch/main/graph/badge.svg?token=KV0cn4jKs2)](https://codecov.io/gh/ome9ax/target-core)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/target-core.svg)](https://pypi.org/project/target-core/)
[![PyPI version](https://badge.fury.io/py/target-core.svg)](https://badge.fury.io/py/target-core)
[![PyPi project installs](https://img.shields.io/pypi/dm/target-core.svg?maxAge=2592000&label=installs&color=%2327B1FF)](https://pypi.org/project/target-core)

[Singer](https://www.singer.io/) target that uploads loads data to S3 in JSONL format
following the [Singer spec](https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md).

## How to use it

`target-core` is a [Singer](https://singer.io) Target which intend to work with regular [Singer](https://singer.io) Tap.

The Goal is to use this package as a foundation to build other taps focusing on the core value, reducing the energy spent on maintaining the common parts.

## Packages extending the `target-core`
- [`target-s3-jsonl`](https://github.com/ome9ax/target-s3-jsonl)

## Install

First, make sure Python 3 is installed on your system or follow these
installation instructions for [Mac](http://docs.python-guide.org/en/latest/starting/install3/osx/) or
[Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-local-programming-environment-on-ubuntu-16-04).

It's recommended to use a virtualenv:

### Defaults
```bash
python -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install target-core
```

### Head
```bash
python -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install --upgrade https://github.com/ome9ax/target-core/archive/main.tar.gz
```

### Isolated virtual environment
```bash
python -m venv ~/.virtualenvs/target-core
source ~/.virtualenvs/target-core/bin/activate
pip install target-core
deactivate
```

Alternative
```bash
python -m venv ~/.virtualenvs/target-core
~/.virtualenvs/target-core/bin/pip install target-core
```

### To run

Like any other target that's following the singer specificiation:

`some-singer-tap | target-core --config [config.json]`

It's reading incoming messages from STDIN and using the properites in `config.json` to upload data into Postgres.

**Note**: To avoid version conflicts run `tap` and `targets` in separate virtual environments.

### Configuration settings

Running the the target connector requires a `config.json` file. An example with the minimal settings:

```json
{
    "s3_bucket": "my_bucket"
}
```

### Profile based authentication

Profile based authentication used by default using the `default` profile. To use another profile set `aws_profile` parameter in `config.json` or set the `AWS_PROFILE` environment variable.

### Non-Profile based authentication

For non-profile based authentication set `aws_access_key_id` , `aws_secret_access_key` and optionally the `aws_session_token` parameter in the `config.json`. Alternatively you can define them out of `config.json` by setting `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` environment variables.


Full list of options in `config.json`:

| Property                            | Type    | Mandatory? | Description                                                   |
|-------------------------------------|---------|------------|---------------------------------------------------------------|
| naming_convention                   | String  |            | (Default: None) Custom naming convention of the s3 key. Replaces tokens `date`, `stream`, and `timestamp` with the appropriate values.<br><br>Supports datetime and other python advanced string formatting e.g. `{stream:_>8}_{timestamp:%Y%m%d_%H%M%S}.json`.<br><br>Supports "folders" in s3 keys e.g. `my_folder/my_sub_folder/{stream}/export_date={date}/{timestamp}.json`.<br><br>Honors the `s3_key_prefix`,  if set, by prepending the "filename". E.g. naming_convention = `folder1/my_file.json` and s3_key_prefix = `prefix_` results in `folder1/prefix_my_file.json`. |
| timezone_offset                     | Integer |            | Offset value in hour. Use offset `0` hours is you want the `naming_convention` to use `utc` time zone. The `null` values is used by default. |
| memory_buffer                       | Integer |            | Memory buffer's size used before storing the data into the temporary file. 64Mb used by default if unspecified. |
| temp_dir                            | String  |            | (Default: platform-dependent) Directory of temporary JSONL files with RECORD messages. |
| compression                         | String  |            | The type of compression to apply before uploading. Supported options are `none` (default), `gzip`, and `lzma`. For gzipped files, the file extension will automatically be changed to `.json.gz` for all files. For `lzma` compression, the file extension will automatically be changed to `.json.xz` for all files. |

## Test
Install the tools
```bash
pip install .[test,lint]
```

Run pytest
```bash
pytest -p no:cacheprovider
```

## Lint
```bash
flake8 --show-source --statistics --count --extend-exclude .virtualenvs
```

## Release
1. Update the version number at the beginning of `target-core/target_core/__init__.py`
2. Merge the changes PR into `main`
3. Create a tag `git tag -a 1.0.0 -m 'Release version 1.0.0'`
4. Release the new version in github

## License

Apache License Version 2.0
