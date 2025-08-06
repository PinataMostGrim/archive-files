# archive-files
Command line application that archives configurations of files and folders and optionally encrypts
the archive or moves it to a target destination. Encryption is performed using either system `openssl` or `gpg` using
symmetric encryption (passphrase).

### Basic usage:
1. Create a default archive JSON configuration using `python3 archive_files -c [config file path]`
2. Add files or folders to the configuration under the `target_paths` array
3. Validate the configuration using `python3 archive_files -v [config file path]`
4. Perform the archive operation using `python3 archive_files [config file path]`

### Optional usage:
- Decrypt an encrypted archive using `python3 archive_files -d [encrypted archive file] [config file path]`
- Follow symbolic links when archiving using `python3 archive_files -f [config file path]` (symlinks are ignored by default)


### Optional configuration:
- `destination_folder` holds a path where the archive will be moved on completion
- `compression_folder` holds a path where the archive will be created before encryption/moving (useful for limited local space)
- `passphrase` enables archive encryption. Defaults to `openssl`.
- `encryption_method` specifies an encryption method. Valid options are `gpg` and `openssl`.
- `archive_prefix` specifies an optional prefix for the archive
- `timestamp` specifies that a timestamp should be applied as a suffix to the archive
- `compress_level` specifies the compression value used. Values must be in the range from 0-9.
- `cleanup` specifies the intermediate archive should be removed on completion, if encryption or file relocation is enabled.
- `follow_symlinks` specifies whether symbolic links should be followed when archiving. Default is `false`.
- `ignore_patterns` specifies an array of glob patterns for files and directories to exclude from the archive.


### Requirements
- Python 3
- (Optional) `openssl` accessible via the PATH environment variable
- (Optional) `gpg` accessible via the PATH environment variable


### Usage
```
usage: archive_files.py [-h] [-c] [-v] [-d DECRYPT] [-f] config_file

Copies files and folders into a password protected archive and moves the archive to a target destination

positional arguments:
  config_file           Backup configuration file

optional arguments:
  -h, --help            show this help message and exit
  -c, --create-config   Create a new backup configuration file
  -v, --validate        Validates JSON configuration file without performing backup
  -d DECRYPT, --decrypt DECRYPT
                        Decrypt archive file
  -f, --follow-symlinks Follow symbolic links when archiving (symlinks are ignored by default)
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
  "cleanup": false,
  "follow_symlinks": false,
  "compression_folder": "",
  "ignore_patterns": []
}
```

### Ignore Patterns Examples

The `ignore_patterns` field supports glob-style patterns to exclude files and directories from the archive. **Important**: Pattern syntax affects matching behavior, especially on Windows systems.

#### Pattern Format Guidelines:
- **For directories**: Use `**/Library` or `Library` (without trailing slash)
- **Avoid**: `**/Library/` (trailing slash may not match on Windows)
- **For files**: Use `*.tmp`, `*.log`, etc.
- **Cross-platform**: Patterns work with both `/` and `\` path separators

#### Basic file patterns:
```json
{
  "ignore_patterns": [
    "*.tmp",
    "*.log",
    "*.pyc",
    "Thumbs.db",
    ".DS_Store"
  ]
}
```

#### Directory patterns:
```json
{
  "ignore_patterns": [
    "__pycache__",
    "node_modules",
    ".git",
    "Library",
    "*.egg-info"
  ]
}
```

#### Path-based patterns:
```json
{
  "ignore_patterns": [
    "**/node_modules",
    "**/Library",
    "temp/*",
    "cache/**",
    "**/build/**",
    "dist/*"
  ]
}
```

#### Unity project example:
```json
{
  "ignore_patterns": [
    "Library",
    "Temp",
    "Logs",
    "*.tmp",
    "UserSettings"
  ]
}
```

#### Combined real-world example:
```json
{
  "ignore_patterns": [
    "*.tmp",
    "*.log",
    "*.pyc",
    "__pycache__",
    "node_modules",
    ".git/**",
    "**/build/**",
    "temp/*",
    "*.egg-info",
    "Library",
    "Logs"
  ]
}
```

### Compression Folder Usage

The `compression_folder` option allows you to specify where the archive is created before encryption or moving to the final destination. This is useful when:

- Local disk space is limited
- You want to compress directly to a network drive
- You need to separate compression and final storage locations

#### Example with compression folder:
```json
{
  "compression_folder": "D:/temp",
  "destination_folder": "//network-drive/backups",
  "target_paths": ["C:/important-data"],
  "passphrase": "mypassword"
}
```

In this example:
1. Archive is created in `D:/temp`
2. Archive is encrypted in `D:/temp`
3. Encrypted archive is moved to `//network-drive/backups`
4. If `cleanup: true`, intermediate files in `D:/temp` are removed

### Important Notes for Ignore Patterns

1. **Directory Matching**: To exclude directories like `Library`, use `Library` or `**/Library` (without trailing slash)
2. **Pattern Testing**: Test your patterns on a small subset first to ensure they work as expected
3. **Case Sensitivity**: Patterns are case-sensitive on most systems
4. **Windows Paths**: The tool automatically handles both forward slashes (`/`) and backslashes (`\`) in patterns
