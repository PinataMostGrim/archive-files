import archive_files
import json
import pytest
import re

from archive_files import Config, Logger, Archiver
from pathlib import Path
from zipfile import ZipFile


# Helpers
def delete_file(file: Path):
    if file.exists():
        file.unlink()


# Fixtures
@pytest.fixture
def test_file() -> Path:
    return Path(__file__).parent / 'test_file.txt'


@pytest.fixture
def test_file2() -> Path:
    return Path(__file__).parent / 'test_file2.txt'


@pytest.fixture
def test_archive() -> Path:
    return Path(__file__).parent / 'test-archive.zip'


@pytest.fixture
def test_config_file() -> Path:
    return Path(__file__).parent / 'test-config.json'


@pytest.fixture
def setup_test_files(test_file, test_file2, test_archive):
    ''' Sets up a test file and tears down the test file and a test archive. '''
    delete_file(test_file)
    delete_file(test_file2)
    delete_file(test_archive)

    test_file.write_text('Test file contents')


@pytest.fixture
def teardown_test_files(test_file, test_file2, test_archive):
    '''' Tears down a test file and test archive. '''
    yield 'teardown_test_files'

    delete_file(test_file)
    delete_file(test_file2)
    delete_file(test_archive)


@pytest.fixture
def setup_teardown_test_config(test_config_file):
    ''' Ensures test configuration file is deleted before and after running a test. '''
    delete_file(test_config_file)
    yield 'teardown_test_config'
    delete_file(test_config_file)


@pytest.fixture
def basic_configuration():
    return {'target_paths': ['test_file.txt']}


@pytest.fixture
def default_configuration():
    return {
        'destination_folder': 'example_folder/',
        'target_paths': [
            'test_file.txt',
        ],
        'passphrase': 'password',
        'encryption_method': 'openssl',
        'archive_prefix': 'test-archive',
        'timestamp': False,
        'compress_level': 5,
        'cleanup': True,
    }


# Patches
@pytest.fixture
def patch_get_short_timestamp(monkeypatch):
    def mock_get_short_timestamp():
        return '16:34:43'

    monkeypatch.setattr(Logger, 'get_short_timestamp', mock_get_short_timestamp)


@pytest.fixture
def patch_get_full_timestamp(monkeypatch):
    def mock_get_full_timestamp():
        return '2022-07-22T160455'

    monkeypatch.setattr(Logger, 'get_full_timestamp', mock_get_full_timestamp)


# Config tests
def test_configuration_initialization(default_configuration):
    ''' Test that Config attributes are assigned from dictionary. '''
    config = Config(default_configuration)
    assert config.destination_folder == 'example_folder/'
    assert config.target_paths == ['test_file.txt']
    assert config.passphrase == 'password'
    assert config.encryption_method == 'openssl'
    assert config.archive_prefix == 'test-archive'
    assert config.timestamp is False
    assert config.compress_level == 5
    assert config.cleanup is True


def test_configuration_default_values():
    ''' Test that Config attributes receive a default value. '''
    config = Config({'target_paths': ['sample_file_name.txt']})
    assert config.destination_folder == ''
    assert config.passphrase == ''
    assert config.encryption_method == 'openssl'
    assert config.archive_prefix == 'Backup'
    assert config.timestamp is True
    assert config.compress_level == 9
    assert config.cleanup is False


def test_configuration_requires_target_paths():
    '''
    Tests that Config raises a KeyError if 'target_paths' is not present in the
    initialization dictionary.
    '''
    empty_configuration = {}
    with pytest.raises(KeyError):
        config = Config(empty_configuration)


# Logger tests
def test_logger_info(capsys, patch_get_short_timestamp):
    ''' Test that Logger.info() has the proper prefix. '''
    Logger.info('Test message')
    captured = capsys.readouterr()
    assert captured.out == '[16:34:43][INFO]: Test message\n'


def test_logger_error(capsys, patch_get_short_timestamp):
    ''' Test that Logger.error() has the proper prefix. '''
    Logger.error('Test message')
    captured = capsys.readouterr()
    assert captured.out == '[16:34:43][ERROR]: Test message\n'


def test_logger_get_short_timestamp():
    '''
    Test that Logger.get_short_timestamp() has the correct format.
    e.g. '17:07:19'
    '''
    timestamp = Logger.get_short_timestamp()
    match = re.search(r'\d{2}:\d{2}:\d{2}', timestamp)
    assert match is not None


def test_logger_get_full_timestamp():
    '''
    Test that Logger.get_full_timestamp() has the correct format.
    e.g. '2022-07-17T170719'
    '''
    timestamp = Logger.get_full_timestamp()
    match = re.search(r'\d{4}-\d{2}-\d{2}T\d{6}', timestamp)
    assert match is not None


# Archiver tests
def test_archiver_add_to_archive(test_file, test_archive, setup_test_files, teardown_test_files):
    ''' Tests that Archiver adds a test file to a test archive. '''
    archived_test_file = test_file.relative_to(test_file.anchor)

    config = Config({'target_paths': [str(test_file)]})
    config.compress_level = 1

    archiver = Archiver(config)
    archiver.add_to_archive(test_archive, test_file)

    with ZipFile(test_archive, mode='r') as zip_file:
        files = zip_file.namelist()
        assert str(archived_test_file.as_posix()) in files


def test_archiver_get_archive_path(basic_configuration, patch_get_full_timestamp):
    ''' Test that 'Archiver.get_archive_path()'' returns valid Path objects. '''
    config = Config(basic_configuration)
    config.timestamp = False
    archiver = Archiver(config)

    archive_path = archiver.get_archive_path()
    assert str(archive_path) == 'Backup.zip'

    archiver.config.archive_prefix = 'test_archive'
    archive_path = archiver.get_archive_path()
    assert str(archive_path) == 'test_archive.zip'

    archiver.config.timestamp = True
    archive_path = archiver.get_archive_path()
    assert str(archive_path) == 'test_archive-2022-07-22T160455.zip'


def test_archiver_move_file(test_file, test_file2, basic_configuration, setup_test_files, teardown_test_files):

    config = Config(basic_configuration)
    archiver = Archiver(config)
    archiver.move_file(test_file, test_file2)

    assert test_file2.exists()


def test_archiver_move_file_safety(test_file, basic_configuration, setup_test_files, teardown_test_files):
    '''Tests that 'Archiver.move_file()' will not overwrite an existing file. '''
    config = Config(basic_configuration)
    archiver = Archiver(config)

    with pytest.raises(SystemExit):
        archiver.move_file(test_file, test_file)


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
def test_create_default_config(test_config_file, setup_teardown_test_config):
    '''
    Tests that 'archive_files.create_config_file()' creates a default configuration at
    the given path.
    '''
    archive_files.create_default_config_file(test_config_file)

    assert test_config_file.exists()

    with open(test_config_file, 'r') as read_file:
        config_data = json.load(read_file)
    assert Config.DEFAULT_CONFIG['destination_folder'] == config_data['destination_folder']
    assert Config.DEFAULT_CONFIG['target_paths'] == config_data['target_paths']
    assert Config.DEFAULT_CONFIG['passphrase'] == config_data['passphrase']
    assert Config.DEFAULT_CONFIG['encryption_method'] == config_data['encryption_method']
    assert Config.DEFAULT_CONFIG['archive_prefix'] == config_data['archive_prefix']
    assert Config.DEFAULT_CONFIG['timestamp'] == config_data['timestamp']
    assert Config.DEFAULT_CONFIG['compress_level'] == config_data['compress_level']
    assert Config.DEFAULT_CONFIG['cleanup'] == config_data['cleanup']


def test_create_config_fails_on_overwrite(test_config_file, setup_teardown_test_config):
    '''
    Tests that 'archive_files.create_config_file()' fails to overwrite an existing configuration file.
    '''
    with open(test_config_file, 'w', encoding='utf-8') as f:
        f.write('Test file contents')

    with pytest.raises(SystemExit):
        archive_files.create_default_config_file(test_config_file)

    with open(test_config_file, 'r', encoding='utf-8') as f:
        data = f.read()

    assert data == 'Test file contents'


def test_get_human_readable_duration():
    '''
    Tests that 'get_human_readable_duration()' generates valid human readable time-code strings.
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
