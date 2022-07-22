import archive_files
import pytest
import re

from archive_files import Config, Logger, Archiver


# Config tests
@pytest.fixture
def default_configuration():
    return {
        "destination_folder": "example_folder/",
        "target_paths": [
            "sample_file_name.txt",
        ],
        "passphrase": "password",
        "encryption_method": "openssl",
        "archive_prefix": "test-archive",
        "timestamp": False,
        "compress_level": 5,
        "cleanup": True,
    }


def test_configuration_initialization(default_configuration):
    '''Test that Config attributes are assigned from dictionary'''
    config = Config(default_configuration)
    assert config.destination_folder == "example_folder/"
    assert config.target_paths == ["sample_file_name.txt"]
    assert config.passphrase == "password"
    assert config.encryption_method == "openssl"
    assert config.archive_prefix == "test-archive"
    assert config.timestamp is False
    assert config.compress_level == 5
    assert config.cleanup is True


def test_configuration_default_values():
    '''Test that Config attributes receive a default value'''
    config = Config({"target_paths": ["sample_file_name.txt"]})
    assert config.destination_folder == ""
    assert config.passphrase == ""
    assert config.encryption_method == "openssl"
    assert config.archive_prefix == "Backup"
    assert config.timestamp is True
    assert config.compress_level == 9
    assert config.cleanup is False


def test_configuration_requires_target_paths():
    '''Tests that Config raises a KeyError if 'target_paths' is not present in the
    initialization dictionary'''
    empty_configuration = {}
    with pytest.raises(KeyError):
        config = Config(empty_configuration)


# Logger tests
def test_logger_info(capsys, monkeypatch):
    '''Test that Logger.info() has the proper prefix'''
    def mock_get_short_timestamp():
        return '16:34:43'

    monkeypatch.setattr(Logger, 'get_short_timestamp', mock_get_short_timestamp)

    Logger.info('Test message')
    captured = capsys.readouterr()
    assert captured.out == '[16:34:43][INFO]: Test message\n'


def test_logger_error(capsys, monkeypatch):
    '''Test that Logger.error() has the proper prefix'''
    def mock_get_short_timestamp():
        return '16:34:43'

    monkeypatch.setattr(Logger, 'get_short_timestamp', mock_get_short_timestamp)

    Logger.error('Test message')
    captured = capsys.readouterr()
    assert captured.out == '[16:34:43][ERROR]: Test message\n'


def test_logger_get_short_timestamp():
    '''
    Test that Logger.get_short_timestamp() has the correct format
    e.g. '17:07:19'
    '''
    timestamp = Logger.get_short_timestamp()
    match = re.search(r'\d{2}:\d{2}:\d{2}', timestamp)
    assert match is not None


def test_logger_get_full_timestamp():
    '''
    Test that Logger.get_full_timestamp() has the correct format
    e.g. '2022-07-17T170719'
    '''
    timestamp = Logger.get_full_timestamp()
    match = re.search(r'\d{4}-\d{2}-\d{2}T\d{6}', timestamp)
    assert match is not None


# Archiver tests
def test_archiver_encrypt_file(default_configuration):
    '''
    Tests that archiver correctly throws a NotImplementedError when encrypting a file.
    '''
    config = Config(default_configuration)
    archiver = Archiver(config)

    with pytest.raises(NotImplementedError):
        archiver.encrypt_file('input_file', 'output_file')


def test_archiver_decrypt_file(default_configuration):
    '''
    Tests that archiver correctly throws a NotImplementedError when attempting to decrypt a file.
    '''
    config = Config(default_configuration)
    archiver = Archiver(config)

    with pytest.raises(NotImplementedError):
        archiver.decrypt_file('input_file', 'output_file')


# Main tests
def test_get_human_readable_duration():
    '''
    Tests that 'get_human_readable_duration()' generates valid human readable timecode strings.
    '''
    seconds = 1
    human_readable = archive_files.get_human_readable_duration(seconds)
    assert human_readable == "1 second"

    seconds = 2
    human_readable = archive_files.get_human_readable_duration(seconds)
    assert human_readable == "2 seconds"

    seconds = 61
    human_readable = archive_files.get_human_readable_duration(seconds)
    assert human_readable == "1 minute, and 1 second"

    seconds = 121
    human_readable = archive_files.get_human_readable_duration(seconds)
    assert human_readable == "2 minutes, and 1 second"

    seconds = 3661
    human_readable = archive_files.get_human_readable_duration(seconds)
    assert human_readable == "1 hour, 1 minute, and 1 second"

    seconds = 7261
    human_readable = archive_files.get_human_readable_duration(seconds)
    assert human_readable == "2 hours, 1 minute, and 1 second"

    seconds = 3601
    human_readable = archive_files.get_human_readable_duration(seconds)
    assert human_readable == "1 hour, and 1 second"

    seconds = 3660
    human_readable = archive_files.get_human_readable_duration(seconds)
    assert human_readable == "1 hour, and 1 minute"
