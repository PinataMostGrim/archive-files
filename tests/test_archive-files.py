import pytest
import archive_files

from archive_files import Config


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

