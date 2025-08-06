# archive-files

Command line tool for creating encrypted backup archives with configurable file exclusion patterns.

## Quick Start

1. **Create config**: `python archive_files.py -c my-config.json`
2. **Edit paths**: Update `target_paths` and `destination_folder`
3. **Validate**: `python archive_files.py -v my-config.json`
4. **Run backup**: `python archive_files.py my-config.json`

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `target_paths` | Array of files/folders to archive | `[""]` |
| `destination_folder` | Where to move completed archive | `""` |
| `compression_folder` | Temporary folder for compression | `""` |
| `passphrase` | Enables encryption (leave empty to disable) | `"password"` |
| `encryption_method` | `"openssl"` or `"gpg"` | `"openssl"` |
| `archive_prefix` | Archive filename prefix | `"Backup"` |
| `timestamp` | Add timestamp to filename | `true` |
| `compress_level` | Compression level (0-9) | `9` |
| `cleanup` | Delete intermediate files | `false` |
| `follow_symlinks` | Include symbolic links | `false` |
| `ignore_patterns` | Array of glob patterns to exclude | `[]` |

## Ignore Patterns

Use glob-style patterns to exclude files and directories:

```json
{
  "ignore_patterns": [
    "*.tmp",
    "*.log",
    "__pycache__",
    "node_modules",
    ".git",
    "Library",
    "**/build/**"
  ]
}
```

**Pattern tips:**
- For directories: Use `Library` not `Library/`
- Cross-platform: Patterns work with both `/` and `\` separators
- Wildcards: `*` matches files, `**` matches directories recursively

## Example Configurations

See included example files:
- `example-simple.json` - Basic backup setup
- `example-config.json` - Full-featured configuration
- `example-unity.json` - Unity project with appropriate exclusions

## Usage

```bash
# Create and customize config
python archive_files.py -c my-backup.json

# Validate configuration
python archive_files.py -v my-backup.json

# Run backup
python archive_files.py my-backup.json

# Decrypt archive
python archive_files.py -d encrypted-file.zip.enc my-backup.json

# Follow symlinks (override config)
python archive_files.py -f my-backup.json
```

## Requirements

- Python 3
- (Optional) OpenSSL or GPG for encryption
