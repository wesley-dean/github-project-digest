from __future__ import annotations

import pytest

from github_project_digest.config import DEFAULT_FILTER, load_config


def test_load_config_reads_required_values_and_defaults(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER", "wesley-dean")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "1")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER_TYPE", "user")
    monkeypatch.setenv("GITHUB_USER", "@me")

    config = load_config()

    assert config.github_token == "token"
    assert config.project_owner == "wesley-dean"
    assert config.project_number == 1
    assert config.project_owner_type == "user"
    assert config.github_user == "@me"
    assert config.recipient_email is None
    assert config.filter_query == DEFAULT_FILTER
    assert config.smtp is None


def test_load_config_builds_smtp_config_when_user_contains_email(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER", "wesley-dean")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "1")
    monkeypatch.setenv("GITHUB_USER", "octocat:to@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM", "from@example.com")
    monkeypatch.setenv("SMTP_SUBJECT", "Daily tasks")

    config = load_config()

    assert config.github_user == "octocat"
    assert config.recipient_email == "to@example.com"
    assert config.smtp is not None
    assert config.smtp.host == "smtp.example.com"
    assert config.smtp.port == 587
    assert config.smtp.sender == "from@example.com"
    assert config.smtp.recipient == "to@example.com"
    assert config.smtp.subject == "Daily tasks"
    assert config.smtp.use_tls is True
    assert config.smtp.use_ssl is False


def test_load_config_rejects_invalid_output_format(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER", "wesley-dean")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "1")
    monkeypatch.setenv("DIGEST_OUTPUT_FORMAT", "pdf")

    with pytest.raises(ValueError, match="DIGEST_OUTPUT_FORMAT"):
        load_config()


def test_load_config_treats_github_user_without_email_as_stdout_only(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER", "wesley-dean")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "1")
    monkeypatch.setenv("GITHUB_USER", "octocat")

    config = load_config()

    assert config.github_user == "octocat"
    assert config.recipient_email is None
    assert config.smtp is None


def test_load_config_supports_empty_github_user_with_email(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER", "wesley-dean")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "1")
    monkeypatch.setenv("GITHUB_USER", ":to@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM", "from@example.com")

    config = load_config()

    assert config.github_user == "@me"
    assert config.recipient_email == "to@example.com"
    assert config.smtp is not None


def test_load_config_ignores_shell_user(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER", "wesley-dean")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "1")
    monkeypatch.setenv("USER", "root")

    config = load_config()

    assert config.github_user == "@me"
    assert config.recipient_email is None
