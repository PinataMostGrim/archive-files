# archive-files
Command line application that archives configurations of files and folders and optionally encrypts
the archive or moves it to a target destination. Encryption is performed using either system `openssl` or `gpg` using
symmetric encryption (passphrase).

Basic usage:
1. Create a default archive JSON configuration using `python3 archive_files -c [config file path]`
2. Add files or folders to the configuration under the `python3 target_paths` array
3. Validate the configuration using `python3 archive_files -v [config file path]`
4. Perform the archive operation using `python3 archive_files [config file path]`

Optional usage:
- Decrypt an encrypted archive using `python3 archive_files -d [encrypted archive file] [config file path]`


### Optional configuration:
- `destination_folder` holds a path where the archive will be moved on completion
- `passphrase` enables archive encryption. Defaults to `openssl`.
- `encryption_method` specifies an encryption method. Valid options are `gpg` and `openssl`.
- `archive_prefix` specifies an optional prefix for the archive
- `timestamp` specifies that a timestamp should be applied as a suffix to the archive
- `compress_level` specifies the compression value used. Values must be in the range from 0-9.
- `cleanup` specifies the intermediate archive should be removed on completion, if encryption or file relocation is enabled.


### Requirements
- Python 3
- (Optional) `openssl` accessible via the PATH environment variable
- (Optional) `gpg` accessible via the PATH environment variable


### Usage
```
usage: archive_files.py [-h] [-c] [-v] [-d DECRYPT] config_file

Copies files and folders into a password protected archive and moves the archive to a target destination

positional arguments:
  config_file           Backup configuration file

optional arguments:
  -h, --help            show this help message and exit
  -c, --create-config   Create a new backup configuration file
  -v, --validate        Validates JSON configuration file without performing backup
  -d DECRYPT, --decrypt DECRYPT
                        Decrypt archive file
```

Example configuration file:

```json
{
  "destination_folder": "",
  "target_paths": [
    "F:/Projects/Python/archive-files/Input/test-data",
    "F:/Projects/Python/archive-files/Input/test-file.txt"
  ],
  "passphrase": "password",
  "encryption_method": "openssl",
  "archive_prefix": "Backup",
  "timestamp": true,
  "compress_level": 9,
  "cleanup": false
}
```
