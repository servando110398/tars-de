import json

import pytest

from tars.core import settings


def test_windows_credentials_use_trusted_connection():
    creds = settings.build_credentials("srv", "db", auth="windows")
    assert creds["query"]["Trusted_Connection"] == "yes"
    assert creds["username"] == ""
    assert creds["password"] == ""


def test_sql_credentials_use_login_without_trusted_connection():
    creds = settings.build_credentials("localhost", "test", auth="sql", username="sa", password="secret")
    assert "Trusted_Connection" not in creds["query"]
    assert creds["username"] == "sa"
    assert creds["password"] == "secret"


def test_driver_is_top_level_not_in_query():
    creds = settings.build_credentials("srv", "db")
    assert creds["driver"] == "ODBC Driver 18 for SQL Server"
    assert "driver" not in creds["query"]
    assert creds["query"]["TrustServerCertificate"] == "yes"


def test_unknown_auth_mode_is_rejected():
    with pytest.raises(ValueError):
        settings.build_credentials("srv", "db", auth="kerberos")


def test_saved_credentials_never_contain_the_password(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "creds_path", tmp_path / "creds.json")
    settings.add_credentials("localhost", "test", auth="sql", username="sa")

    saved = json.loads((tmp_path / "creds.json").read_text())
    assert "password" not in saved
    assert saved["auth"] == "sql"


def test_sql_password_comes_from_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "creds_path", tmp_path / "creds.json")
    monkeypatch.setenv(settings.PASSWORD_ENV_VAR, "from-env")
    settings.add_credentials("localhost", "test", auth="sql", username="sa")

    assert settings.load_credentials()["password"] == "from-env"


def test_old_creds_file_with_username_is_treated_as_sql_login(tmp_path, monkeypatch):
    path = tmp_path / "creds.json"
    path.write_text(json.dumps({"host": "localhost", "database": "test", "username": "sa"}))
    monkeypatch.setattr(settings, "creds_path", path)

    creds = settings.load_credentials(password="pw")
    assert "Trusted_Connection" not in creds["query"]
    assert creds["password"] == "pw"


def test_load_credentials_without_saved_connection_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "creds_path", tmp_path / "missing.json")
    assert settings.load_credentials() == {}
