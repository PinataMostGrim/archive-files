'''
Compresses important files from local drive into a password protected archive and moves the archive to the network share.

Requirements:
- 7z installed and accessible via the PATH environment variable

TODO:
- Use Python libraries to encrypt the archive
    - Not sure this will be possible with standard library modules
- Archive all valid paths in one command line execution
    - Check all file paths before starting archive
    - [link](https://superuser.com/a/940884)
    - Time it to see if there is a savings
'''

import argparse
import json
import shutil
import subprocess
import sys
import time

from datetime import datetime
from json.decoder import JSONDecodeError
from pathlib import Path
from subprocess import PIPE, STDOUT
from zipfile import ZipFile, ZIP_DEFLATED


DEFAULT_CONFIG = {
    "password": r"password",
    "destination_folder": r"",
    "target_paths": [
        r"",
    ],
    "cleanup": False,
    "compress_level": 9
}


def add_to_archive(archive_path: Path, target_path: Path, compress_level: int = 9):
    '''Adds the target path to an archive.'''

    log_info(f'Archiving "{target_path}"')

    if not target_path.exists():
        log_error(f'Unable to archive "{target_path}"; path does not exist')
        return

    with ZipFile(archive_path, mode='a', compression=ZIP_DEFLATED, compresslevel=compress_level) as archive:
        if target_path.is_dir():
            for file_path in target_path.rglob("*"):
                archive.write(
                    file_path,
                    arcname=file_path.relative_to(target_path.anchor))
        else:
            archive.write(
                    target_path,
                    arcname=target_path.relative_to(target_path.anchor))


def add_to_archive_7z(archive_path: Path, target_path: Path, password: str):
    '''
    Adds the target path to the archive.
    '''

    log_info(f'Archiving "{target_path}"')

    if not target_path.exists():
        log_error(f'Unable to archive "{target_path}"; path does not exist')
        return

    subprocess.run(['7z', 'a', archive_path, target_path, f'-p{password}'], check=True, capture_output=True)


def move_file(file: Path, destination_path: Path):
    '''
    Moves a file to a destination folder.
    '''

    target_path = Path(destination_path / file)
    log_info(f'Moving "{file}" to "{target_path}"')

    if target_path.exists():
        log_error(f'Unable to move file to destination; target path "{target_path}" already exists')
        sys.exit(1)

    # shutil.copy() does not preserve file metadata. If this is something we need in
    # the future, use shutil.copy2() instead
    shutil.copy(file, destination_path)


def create_config(config_file: Path):
    '''
    Creates a default configuration file at the specified path.
    '''

    # TODO: An exception is thrown if the file has no extension
    # Something to do with Path vs WindowsPath objects
    if (config_file.suffix != '.json'):
        config_file.suffix = config_file.with_suffix('.json')

    if (config_file.exists()):
        log_error(f'Unable to create backup configuration file; "{config_file}" already exists')
        sys.exit(1)

    with open(config_file, 'w') as write_file:
        json.dump(DEFAULT_CONFIG, write_file, indent=2)

    log_info(f'Configuration created at "{config_file}"')


def load_config(config_file: Path):
    '''
    Loads configuration from the specified configuration file.
    '''

    if (not config_file.exists()):
        log_error(f'Unable to load configuration file; "{config_file}" does not exist')
        sys.exit(1)

    try:
        with open(config_file, "r") as read_file:
            config_data = json.load(read_file)
    except:
        log_error(f'Invalid configuration file: "{config_file}"')
        raise

    return config_data


def validate_config(config_file: Path):
    '''
    Loads the specified configuration file to see if JSON deserialization works.
    '''

    config = load_config(config_file)

    try:
        password = config['password']
        destination = config['destination_folder']
        target_paths = config['target_paths']
        cleanup = config['cleanup']
        cleanup = config['compress_level']
    except JSONDecodeError as ex:
        log_error(f'Configuration file "{config_file}" is missing a required key')
        raise

    log_info(f'Configuration file "{config_file}" validated')


def get_human_readable_duration(seconds):
    '''
    Returns a value of seconds converted into a human readable, time formatted string.
    '''

    hours = seconds // 3600
    minutes = seconds // 60 % 60
    seconds = seconds % 60

    hour_string = 'hours' if hours > 1 else 'hour'
    minute_string = 'minutes' if minutes > 1 else 'minute'
    second_string = 'seconds' if seconds > 1 else 'second'

    if hours > 0:
        return f'{hours} {hour_string}, {minutes} {minute_string} and {seconds:0.0f} {second_string}'

    if minutes > 0:
        return f'{minutes} {minute_string} and {seconds:0.0f} {second_string}'

    return f'{seconds:0.0f} {second_string}'


def log_info(message: str):
    print(f'[{get_short_timestamp()}][INFO]: {message}')


def log_error(message: str):
    print(f'[{get_short_timestamp()}][ERROR]: {message}')


def get_short_timestamp():
    return datetime.now().strftime("%H:%M:%S")


def get_full_timestamp():
    return datetime.now().strftime('%Y-%m-%dT%H%M%S')


def parse_args():
    '''
    Parse and return command line args.
    '''

    parser = argparse.ArgumentParser(
        description='Copies files and folders into a password protected archive and moves the archive to a target destination')
    parser.add_argument('config_file', type=str, help='Bacup configuration file')
    parser.add_argument('-c', '--create-config', action='store_true', help='Create a new backup configuration file')
    parser.add_argument('-v', '--validate', action='store_true',
                        help='Validates JSON configuration file without performing backup')

    return parser.parse_args()


def main():

    start_time = time.perf_counter()
    args = parse_args()

    config_file = Path(args.config_file)
    if args.create_config:
        create_config(config_file)
        sys.exit()

    if args.validate:
        validate_config(config_file)
        sys.exit()

    config = load_config(config_file)

    timestamp = get_full_timestamp()
    archive_path = Path(f'Backup-{timestamp}.zip')
    log_info(f'Backing up files to "{archive_path}"')

    if (archive_path.exists()):
        log_error(f'Unable to create backup archive; archive path "{archive_path}" already exists')
        sys.exit(1)

    # Archive all target paths
    password = config['password']
    for path in config['target_paths']:
        add_to_archive(archive_path, Path(path), config['compress_level'])

    # Move archive to destination path
    if config['destination_folder']:
        destination_path = Path(config['destination_folder'])
        move_file(archive_path, destination_path)

    if (config['cleanup']):
        log_info(f'Deleting local archive file "{archive_path}"')
        archive_path.unlink()

    end_time = time.perf_counter()
    duration = end_time - start_time
    log_info(f'Backup completed in {get_human_readable_duration(duration)}')


if __name__ == '__main__':
    main()
