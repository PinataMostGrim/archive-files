'''
Compresses important files from local drive into a password protected archive and moves the archive to the network share.

Requirements:
- openssl accessible via the PATH environment variable
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
from zipfile import ZipFile, ZIP_DEFLATED


DEFAULT_CONFIG = {
    "passphrase": r"password",
    "destination_folder": r"",
    "target_paths": [
        r"",
    ],
    "archive_prefix": "Backup",
    "timestamp": True,
    "cleanup": False,
    "compress_level": 9
}


class Config(object):
    def __init__(self, config: dict):
        try:
            self.passphrase = config['passphrase'] if 'passphrase' in config else ""
            self.destination_folder = config['destination_folder'] if 'destination_folder' in config else ""
            self.target_paths = config['target_paths']
            self.archive_prefix = config['archive_prefix'] if 'archive_prefix' in config else "Backup"
            self.timestamp = config['timestamp'] if 'timestamp' in config else True
            self.cleanup = config['cleanup'] if 'cleanup' in config else False
            self.compress_level = config['compress_level'] if 'compress_level' in config else 9
        except KeyError as ex:
            log_error(f'Configuration file is missing a required key {ex}')
            raise


class BackupResult(object):
    def __init__(self):
        self.move_archive = False
        self.archive_moved = False
        self.move_encrypted = False
        self.encrypted_moved = False
        self.archive_encrypted = False
        self.cleanup_archive = False
        self.cleanup_encrypted = False


def add_to_archive(archive_path: Path, target_path: Path, compress_level: int = 9):
    '''
    Adds the target path to an archive.
    '''

    if not target_path.exists():
        log_error(f'"{target_path}" does not exist - unable to archive')
        return

    log_info(f'Archiving "{target_path}"')

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


def encrypt_file(input_path: Path, output_path: Path, passphrase: str):
    '''
    Encrypts a file using openssl and AES-256.
    '''

    if not input_path.exists():
        log_error(f'Input path "{input_path}" does not exist - unable to encrypt file')
        return

    if output_path.exists():
        log_error(f'Output path "{output_path}" already exist - unable to encrypt file')
        return

    if not has_openssl():
        log_error('Openssl is not available on PATH variable - unable to encrypt archive')
        return

    log_info(f'Encrypting file "{input_path}" into "{output_path}"')
    encrypt_command = [
        'openssl',
        'enc',
        '-aes-256-cbc',
        '-md',
        'sha512',
        '-pbkdf2',
        '-iter',
        '10000',
        '-salt',
        '-k',
        passphrase,
        '-in',
        input_path,
        '-out',
        output_path
    ]

    subprocess.run(encrypt_command, check=True, capture_output=True)


def decrypt_file(input_path: Path, output_path: Path, passphrase: str):
    '''
    Decrypts a file using openssl and AES-256.
    '''

    if not input_path.exists():
        log_error(f'Input path "{input_path}" does not exist - unable to decrypt file')
        return

    if output_path.exists():
        log_error(f'Output path "{output_path}" already exist - unable to decrypt file')
        return

    if not has_openssl():
        log_error('Openssl is not available on PATH variable - unable to decrypt archive')
        return

    log_info(f'Decrypting file "{input_path}" into "{output_path}"')
    decrypt_command = [
        'openssl',
        'enc',
        '-aes-256-cbc',
        '-md',
        'sha512',
        '-pbkdf2',
        '-iter',
        '10000',
        '-salt',
        '-k',
        passphrase,
        '-in',
        input_path,
        '-out',
        output_path,
        '-d'
    ]

    subprocess.run(decrypt_command, check=True, capture_output=True)
    log_info('Decryption complete')


def has_openssl():
    '''
    Returns True if openssl is reachable via PATH, False otherwise.
    '''

    try:
        subprocess.run(['openssl', 'help'], check=True, capture_output=True)
    except FileNotFoundError:
        return False

    return True


def move_file(file: Path, destination_path: Path):
    '''
    Moves a file to a destination folder.
    '''

    target_path = Path(destination_path / file)
    log_info(f'Moving "{file}" to "{target_path}"')

    if target_path.exists():
        log_error(f'Target path "{target_path}" already exists - unable to move file to destination')
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
        log_error(f'"{config_file}" already exists - unable to create backup configuration file')
        sys.exit(1)

    with open(config_file, 'w') as write_file:
        json.dump(DEFAULT_CONFIG, write_file, indent=2)

    log_info(f'Configuration created at "{config_file}"')


def load_config(config_file: Path):
    '''
    Loads configuration from the specified configuration file.
    '''

    if (not config_file.exists()):
        log_error(f'"{config_file}" does not exist - unable to load configuration file')
        sys.exit(1)

    try:
        with open(config_file, "r") as read_file:
            config_data = json.load(read_file)
    except JSONDecodeError:
        log_error(f'Invalid configuration file: "{config_file}"')
        raise

    return Config(config_data)


def validate_config(config_file: Path):
    '''
    Loads the specified configuration file to see if JSON deserialization works.
    '''

    _ = load_config(config_file)
    log_info(f'Configuration file "{config_file}" validated')


def get_human_readable_duration(seconds):
    '''
    Returns a value of seconds converted into a human readable, time formatted string.
    '''

    hours = int(seconds // 3600)
    minutes = int(seconds // 60 % 60)
    seconds = int(seconds % 60)

    hour_string = 'hour' if hours == 1 else 'hours'
    minute_string = 'minute' if minutes == 1 else 'minutes'
    second_string = 'second' if seconds == 1 else 'seconds'

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
    parser.add_argument('config_file', type=str, help='Backup configuration file')
    parser.add_argument('-c', '--create-config', action='store_true', help='Create a new backup configuration file')
    parser.add_argument('-v', '--validate', action='store_true',
                        help='Validates JSON configuration file without performing backup')
    parser.add_argument('-d', '--decrypt', type=str, default="", help='Decrypt archive file')

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
    results = BackupResult()

    # Perform decryption if requested
    if args.decrypt:
        input_path = Path(args.decrypt)
        output_path = Path(input_path.with_name(input_path.stem))
        decrypt_file(input_path, output_path, config.passphrase)
        sys.exit()

    if config.timestamp:
        timestamp = get_full_timestamp()
        archive_path = Path(f'{config.archive_prefix}-{timestamp}.zip')
    else:
        archive_path = Path(f'{config.archive_prefix}.zip')

    log_info(f'Archiveing files to "{archive_path}"')

    if (archive_path.exists()):
        log_error(f'Archive path "{archive_path}" already exists - unable to create backup archive')
        sys.exit(1)

    # Archive all target paths
    for path in config.target_paths:
        add_to_archive(archive_path, Path(path), config.compress_level)

    results.move_archive = True if config.destination_folder and archive_path.exists else False
    results.move_encrypted = False

    # Encrypt archive if config contains a passphrase
    encrypted_path = ""
    if config.passphrase:
        encrypted_path = archive_path.with_suffix(archive_path.suffix + '.enc')
        if encrypted_path.exists():
            log_error('"{encrypted_path}" already exists - unable to output encrypted file ')
            sys.exit(1)

        encrypt_file(archive_path, encrypted_path, config.passphrase)
        results.archive_encrypted = encrypted_path.exists()
        results.move_archive = False
        results.move_encrypted = True if config.destination_folder and encrypted_path.exists() else False

        if not results.archive_encrypted:
            log_error('Encryption failed - preventing archive relocation to destination folder')

    # Move output to destination path
    if results.move_archive:
        destination_path = Path(config.destination_folder)
        move_file(archive_path, destination_path)
        results.archive_moved = True

    if results.move_encrypted:
        destination_path = Path(config.destination_folder)
        move_file(encrypted_path, destination_path)
        results.encrypted_moved = True

    if (config.cleanup):
        results.cleanup_archive = (results.archive_encrypted or results.archive_moved) and archive_path.exists()
        results.cleanup_encrypted = results.archive_encrypted and results.encrypted_moved and encrypted_path.exists()

        if results.cleanup_archive:
            log_info(f'Deleting local file "{archive_path}"')
            archive_path.unlink()

        if results.cleanup_encrypted:
            log_info(f'Deleting local file "{encrypted_path}"')
            encrypted_path.unlink()

    end_time = time.perf_counter()
    duration = end_time - start_time
    log_info(f'Archive completed in {get_human_readable_duration(duration)}')


if __name__ == '__main__':
    main()
