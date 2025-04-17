"""
Compresses files into an archive and optionally encrypts the archive and/or optionally moves the archive to a target destination.

Requirements:
- (Optional) openssl accessible via the PATH environment variable
- (Optional) gpg accessible via the PATH environment variable
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from json.decoder import JSONDecodeError
from pathlib import Path
from subprocess import CalledProcessError
from zipfile import ZIP_DEFLATED, ZipFile


class Config(object):
    DEFAULT_CONFIG = {
        "destination_folder": r"",
        "target_paths": [
            r"",
        ],
        "passphrase": r"password",
        "encryption_method": "openssl",
        "archive_prefix": "Backup",
        "timestamp": True,
        "compress_level": 9,
        "cleanup": False,
        "follow_symlinks": False,
    }

    def __init__(self, config: dict):
        try:
            self.destination_folder = (
                config["destination_folder"] if "destination_folder" in config else ""
            )
            self.target_paths = config["target_paths"]
            self.passphrase = config["passphrase"] if "passphrase" in config else ""
            self.encryption_method = (
                config["encryption_method"]
                if "encryption_method" in config
                else "openssl"
            )
            self.archive_prefix = (
                config["archive_prefix"] if "archive_prefix" in config else "Backup"
            )
            self.timestamp = config["timestamp"] if "timestamp" in config else True
            self.compress_level = (
                config["compress_level"] if "compress_level" in config else 9
            )
            self.cleanup = config["cleanup"] if "cleanup" in config else False
            self.follow_symlinks = config["follow_symlinks"] if "follow_symlinks" in config else False
        except KeyError as ex:
            Logger.error(f"Configuration file is missing a required key {ex}")
            raise


class Logger(object):
    @classmethod
    def info(cls, message: str):
        print(f"[{Logger.get_short_timestamp()}][INFO]: {message}")

    @classmethod
    def error(cls, message: str):
        print(f"[{Logger.get_short_timestamp()}][ERROR]: {message}")

    @classmethod
    def get_short_timestamp(cls):
        return datetime.now().strftime("%H:%M:%S")

    @classmethod
    def get_full_timestamp(cls):
        return datetime.now().strftime("%Y-%m-%dT%H%M%S")


class Archiver(object):
    def __init__(self, config: Config):
        self.config = config

        self.move_archive = False
        self.archive_moved = False
        self.archive_encrypted = False
        self.move_encrypted = False
        self.encrypted_moved = False
        self.cleanup_archive = False
        self.cleanup_encrypted = False

        # Statistics for tracking file processing
        self.files_processed = 0
        self.files_skipped = 0
        self.files_failed = 0
        self.failed_files = []

    def perform_archive(self):
        """Performs archive and optional encryption."""

        archive_path = self.get_archive_path()

        Logger.info(f'Archiving files to "{archive_path}"')

        if archive_path.exists():
            Logger.error(
                f'Archive path "{archive_path}" already exists - unable to create backup archive'
            )
            sys.exit(1)

        # Archive files
        for path in self.config.target_paths:
            self.add_to_archive(archive_path, Path(path))

        # Log summary of archiving results
        Logger.info(f"Archive summary: {self.files_processed} files processed, {self.files_skipped} files skipped")
        if self.files_failed > 0:
            Logger.error(f"{self.files_failed} files failed to archive")
            # Only show first 10 failed files to avoid flooding the log
            if len(self.failed_files) > 10:
                Logger.error(f"First 10 failed files: {', '.join(self.failed_files[:10])}")
                Logger.error(f"... and {len(self.failed_files) - 10} more")
            else:
                Logger.error(f"Failed files: {', '.join(self.failed_files)}")

        self.move_archive = (
            True if self.config.destination_folder and archive_path.exists else False
        )

        # Encrypt archive if config contains a passphrase
        encrypted_path = ""
        if self.config.passphrase:
            encrypted_path = archive_path.with_suffix(archive_path.suffix + ".enc")
            if encrypted_path.exists():
                Logger.error(
                    '"{encrypted_path}" already exists - unable to output encrypted file '
                )
                sys.exit(1)

            self.encrypt_file(archive_path, encrypted_path)
            self.archive_encrypted = encrypted_path.exists()
            self.move_archive = False
            self.move_encrypted = (
                True
                if self.config.destination_folder and encrypted_path.exists()
                else False
            )

            if not self.archive_encrypted:
                Logger.error(
                    "Encryption failed - preventing archive relocation to destination folder"
                )

        # Move output to destination path
        if self.move_archive:
            destination_path = Path(self.config.destination_folder) / archive_path.name
            self.move_file(archive_path, destination_path)
            self.archive_moved = True

        if self.move_encrypted:
            destination_path = (
                Path(self.config.destination_folder) / encrypted_path.name
            )
            self.move_file(encrypted_path, destination_path)
            self.encrypted_moved = True

        # Cleanup
        if self.config.cleanup:
            self.cleanup_archive = (
                self.archive_encrypted or self.archive_moved
            ) and archive_path.exists()
            self.cleanup_encrypted = (
                self.archive_encrypted
                and self.encrypted_moved
                and encrypted_path.exists()
            )

            if self.cleanup_archive:
                Logger.info(f'Deleting local file "{archive_path}"')
                archive_path.unlink()

            if self.cleanup_encrypted:
                Logger.info(f'Deleting local file "{encrypted_path}"')
                encrypted_path.unlink()

    def get_archive_path(self) -> Path:
        """Returns a Path object for the archive."""
        if self.config.timestamp:
            timestamp = Logger.get_full_timestamp()
            return Path(f"{self.config.archive_prefix}-{timestamp}.zip")
        else:
            return Path(f"{self.config.archive_prefix}.zip")

    def add_to_archive(self, archive_path: Path, target_path: Path):
        """Adds the file or folder at target path to an archive."""
        if not target_path.exists():
            Logger.error(f'"{target_path}" does not exist - unable to archive')
            return

        Logger.info(f'Archiving "{target_path}"')

        compress_level = (
            0
            if self.config.compress_level < 0
            else 9
            if self.config.compress_level > 9
            else self.config.compress_level
        )

        try:
            with ZipFile(
                archive_path,
                mode="a",
                compression=ZIP_DEFLATED,
                compresslevel=compress_level,
            ) as archive:
                if target_path.is_dir():
                    # Process directory contents
                    for file_path in target_path.rglob("*"):
                        try:
                            # Skip symlinks unless configured to follow them
                            if file_path.is_symlink() and not self.config.follow_symlinks:
                                Logger.info(f'Skipping symlink "{file_path}"')
                                self.files_skipped += 1
                                continue

                            # Skip non-files (directories are automatically created when files are added)
                            if not file_path.is_file():
                                continue

                            archive.write(
                                file_path, arcname=file_path.relative_to(target_path.anchor)
                            )
                            self.files_processed += 1

                        except (FileNotFoundError, PermissionError, ValueError, OSError) as ex:
                            # Log error but continue with other files
                            Logger.error(f"Error archiving file '{file_path}': {ex}")
                            self.files_failed += 1
                            self.failed_files.append(str(file_path))

                        except Exception as ex:
                            # Catch any other unforeseen exceptions
                            Logger.error(f"Unexpected error when archiving '{file_path}': {ex}")
                            self.files_failed += 1
                            self.failed_files.append(str(file_path))
                else:
                    # Process single file
                    try:
                        # Skip symlinks unless configured to follow them
                        if target_path.is_symlink() and not self.config.follow_symlinks:
                            Logger.info(f'Skipping symlink "{target_path}"')
                            self.files_skipped += 1
                            return

                        archive.write(
                            target_path, arcname=target_path.relative_to(target_path.anchor)
                        )
                        self.files_processed += 1

                    except (FileNotFoundError, PermissionError, ValueError, OSError) as ex:
                        Logger.error(f"Error archiving file '{target_path}': {ex}")
                        self.files_failed += 1
                        self.failed_files.append(str(target_path))

                    except Exception as ex:
                        Logger.error(f"Unexpected error when archiving '{target_path}': {ex}")
                        self.files_failed += 1
                        self.failed_files.append(str(target_path))

        except Exception as ex:
            # This catches errors at the archive level (e.g., disk full, permissions)
            Logger.error(f"Critical error creating archive: {ex}")
            raise

    def move_file(self, source_file: Path, destination_file: Path):
        """Moves a file to a destination file path."""
        Logger.info(f'Moving "{source_file}" to "{destination_file}"')

        if destination_file.exists():
            Logger.error(
                f'Target path "{destination_file}" already exists - unable to move file to destination'
            )
            sys.exit(1)

        # shutil.copy() does not preserve file metadata. If this is something we need in
        # the future, use shutil.copy2() instead
        shutil.copy(source_file, destination_file)

    def encrypt_file(self, input_path: Path, output_path: Path):
        raise NotImplementedError

    def decrypt_file(self, input_path: Path, output_path: Path):
        raise NotImplementedError


class OpenSSLArchiver(Archiver):
    def encrypt_file(self, input_path: Path, output_path: Path):
        """Encrypts a file using openssl and AES-256."""
        if not input_path.exists():
            Logger.error(
                f'Input path "{input_path}" does not exist - unable to encrypt file'
            )
            return

        if output_path.exists():
            Logger.error(
                f'Output path "{output_path}" already exist - unable to encrypt file'
            )
            return

        if not self.has_openssl():
            Logger.error(
                "Openssl is not accessible through the PATH variable - unable to encrypt archive"
            )
            return

        Logger.info(f'Encrypting file "{input_path}" into "{output_path}"')
        encrypt_command = [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-md",
            "sha512",
            "-pbkdf2",
            "-iter",
            "10000",
            "-salt",
            "-k",
            self.config.passphrase,
            "-in",
            input_path,
            "-out",
            output_path,
        ]

        subprocess.run(encrypt_command, check=True, capture_output=True)

    def decrypt_file(self, input_path: Path, output_path: Path):
        """Decrypts a file using openssl and AES-256."""
        if not input_path.exists():
            Logger.error(
                f'Input path "{input_path}" does not exist - unable to decrypt file'
            )
            return

        if output_path.exists():
            Logger.error(
                f'Output path "{output_path}" already exist - unable to decrypt file'
            )
            return

        if not self.has_openssl():
            Logger.error(
                "Openssl is not accessible through the PATH variable - unable to decrypt archive"
            )
            return

        Logger.info(f'Decrypting file "{input_path}" into "{output_path}"')
        decrypt_command = [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-md",
            "sha512",
            "-pbkdf2",
            "-iter",
            "10000",
            "-salt",
            "-k",
            self.config.passphrase,
            "-in",
            input_path,
            "-out",
            output_path,
            "-d",
        ]

        subprocess.run(decrypt_command, check=True, capture_output=True)
        Logger.info("Decryption complete")

    def has_openssl(self) -> bool:
        """Returns True if openssl is reachable via PATH, False otherwise."""
        try:
            subprocess.run(["openssl", "help"], check=True, capture_output=True)
        except (FileNotFoundError, CalledProcessError):
            return False

        return True


class GPGArchiver(Archiver):
    def encrypt_file(self, input_path: Path, output_path: Path):
        """Encrypts a file using GPG and AES-256."""
        if not input_path.exists():
            Logger.error(
                f'Input path "{input_path}" does not exist - unable to encrypt file'
            )
            return

        if output_path.exists():
            Logger.error(
                f'Output path "{output_path}" already exist - unable to encrypt file'
            )
            return

        if not self.has_gpg():
            Logger.error(
                "GPG is not accessible through the PATH variable - unable to encrypt archive"
            )
            return

        Logger.info(f'Encrypting file "{input_path}" into "{output_path}"')
        encrypt_command = [
            "gpg",
            "--output",
            str(output_path),
            "--cipher-algo",
            "AES256",
            "--passphrase",
            str(self.config.passphrase),
            "--batch",
            "-c",
            input_path,
        ]

        subprocess.run(encrypt_command, check=True, capture_output=True)

    def decrypt_file(self, input_path: Path, output_path: Path):
        """Decrypts a file using GPG and AES-256."""
        if not input_path.exists():
            Logger.error(
                f'Input path "{input_path}" does not exist - unable to decrypt file'
            )
            return

        if output_path.exists():
            Logger.error(
                f'Output path "{output_path}" already exist - unable to decrypt file'
            )
            return

        if not self.has_gpg():
            Logger.error(
                "GPG is not accessible through the PATH variable - unable to decrypt archive"
            )
            return

        Logger.info(f'Decrypting file "{input_path}" into "{output_path}"')
        decrypt_command = [
            "gpg",
            "--cipher-algo",
            "AES256",
            "--passphrase",
            str(self.config.passphrase),
            "--output",
            str(output_path),
            "--batch",
            "--decrypt",
            input_path,
        ]

        subprocess.run(decrypt_command, check=True, capture_output=True)
        Logger.info("Decryption complete")

    def has_gpg(self) -> bool:
        """Returns True if gpg is reachable via PATH, False otherwise."""
        try:
            subprocess.run(["gpg", "help"], check=True, capture_output=True)
        except (FileNotFoundError, CalledProcessError):
            return False

        return True


def create_default_config_file(config_file: Path):
    """Creates a default configuration file at the specified path."""
    # TODO: An exception is thrown if the file has no extension
    # Something to do with Path vs WindowsPath objects
    if config_file.suffix != ".json":
        config_file.suffix = config_file.with_suffix(".json")

    if config_file.exists():
        Logger.error(
            f'"{config_file}" already exists - unable to create backup configuration file'
        )
        sys.exit(1)

    with open(config_file, "w") as write_file:
        json.dump(Config.DEFAULT_CONFIG, write_file, indent=2)

    Logger.info(f'Configuration created at "{config_file}"')


def load_config_file(config_file: Path) -> Config:
    """Loads configuration from the specified configuration file."""
    if not config_file.exists():
        Logger.error(
            f'"{config_file}" does not exist - unable to load configuration file'
        )
        sys.exit(1)

    try:
        with open(config_file, "r") as read_file:
            config_data = json.load(read_file)
    except JSONDecodeError:
        Logger.error(f'Invalid configuration file: "{config_file}"')
        raise

    return Config(config_data)


def validate_config(config_file: Path):
    """Loads the specified configuration file to see if JSON deserialization works."""
    _ = load_config_file(config_file)
    Logger.info(f'Configuration file "{config_file}" validated')


def get_human_readable_duration(seconds) -> str:
    """Returns a value of seconds converted into a human readable, time formatted string."""
    seconds_float = seconds
    hours = int(seconds // 3600)
    minutes = int(seconds // 60 % 60)
    seconds = int(seconds % 60)

    hours_word = "hour" if hours == 1 else "hours"
    minutes_word = "minute" if minutes == 1 else "minutes"
    seconds_word = "second" if seconds == 1 else "seconds"

    hours_string = f"{hours} {hours_word}" if hours > 0 else ""
    minutes_string = f"{minutes} {minutes_word}" if minutes > 0 else ""
    seconds_string = f"{seconds} {seconds_word}" if seconds > 0 else ""

    if hours != 0 and (minutes != 0 or seconds != 0):
        hours_string = f"{hours_string}, "
    if minutes != 0 and seconds != 0:
        minutes_string = f"{minutes_string}, "

    if seconds != 0 and (hours != 0 or minutes != 0):
        seconds_string = f"and {seconds_string}"
    elif minutes != 0 and hours != 0:
        minutes_string = f"and {minutes_string}"

    if hours == 0 and minutes == 0 and seconds == 0:
        seconds_string = f"{seconds_float:.3f} {seconds_word}"

    return f"{hours_string}{minutes_string}{seconds_string}"


def parse_args():
    """Parse and return command line args."""
    parser = argparse.ArgumentParser(
        description="Copies files and folders into a password protected archive and moves the archive to a target destination"
    )
    parser.add_argument("config_file", type=str, help="Backup configuration file")
    parser.add_argument(
        "-c",
        "--create-config",
        action="store_true",
        help="Create a new backup configuration file",
    )
    parser.add_argument(
        "-v",
        "--validate",
        action="store_true",
        help="Validates JSON configuration file without performing backup",
    )
    parser.add_argument(
        "-d", "--decrypt", type=str, default="", help="Decrypt archive file"
    )
    parser.add_argument(
        "-f",
        "--follow-symlinks",
        action="store_true",
        help="Follow symbolic links when archiving (symlinks are ignored by default)",
    )

    return parser.parse_args()


def main():
    start_time = time.perf_counter()
    args = parse_args()

    config_file = Path(args.config_file)
    if args.create_config:
        create_default_config_file(config_file)
        sys.exit()

    if args.validate:
        validate_config(config_file)
        sys.exit()

    config = load_config_file(config_file)
    # Override config follow_symlinks with command line argument if provided
    if args.follow_symlinks:
        config.follow_symlinks = True

    if config.encryption_method.lower() == "gpg":
        archiver = GPGArchiver(config)
    # Default to OpenSSL
    else:
        archiver = OpenSSLArchiver(config)

    # Perform decryption if requested
    if args.decrypt:
        input_path = Path(args.decrypt)
        output_path = Path(input_path.with_name(input_path.stem))
        archiver.decrypt_file(input_path, output_path)
        sys.exit()

    # Perform archive operation and optional encryption
    archiver.perform_archive()

    end_time = time.perf_counter()
    duration = end_time - start_time

    Logger.info(f"Archive completed in {get_human_readable_duration(duration)}")


if __name__ == "__main__":
    main()
