import pytest
import archive_files


@pytest.fixture
def default_configuration():
    return {
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
    }


def test_configuration_init():
    assert True
