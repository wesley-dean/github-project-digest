from __future__ import annotations

import pytest

from github_project_digest.config import (
    DEFAULT_DUE_SOON_DAYS,
    DEFAULT_DUE_UPCOMING_DAYS,
    DEFAULT_FILTER,
    DEFAULT_SEND_EMPTY_EMAIL,
    load_config,
)


def _set_required_project_env(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER", "wesley-dean")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "1")


def _set_smtp_env(monkeypatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM", "from@example.com")
    monkeypatch.setenv("SMTP_SUBJECT", "Daily tasks")


def test_load_config_reads_required_values_and_defaults(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_PROJECT_OWNER_TYPE", "user")
    monkeypatch.setenv("GITHUB_USER", "@me")

    config = load_config()

    assert config.github_token == "token"
    assert config.project_owner == "wesley-dean"
    assert config.project_number == 1
    assert config.project_owner_type == "user"
    assert config.github_user == "@me"
    assert config.recipient_email is None
    assert config.users[0].github_user == "@me"
    assert config.users[0].recipient_email is None
    assert config.users[0].smtp is None
    assert config.filter_query == DEFAULT_FILTER
    assert config.due_soon_days == DEFAULT_DUE_SOON_DAYS
    assert config.due_upcoming_days == DEFAULT_DUE_UPCOMING_DAYS
    assert config.send_empty_email is DEFAULT_SEND_EMPTY_EMAIL
    assert config.smtp is None


def test_load_config_builds_smtp_config_when_user_contains_email(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_USER", "octocat:to@example.com")
    _set_smtp_env(monkeypatch)

    config = load_config()

    assert config.github_user == "octocat"
    assert config.recipient_email == "to@example.com"
    assert len(config.users) == 1
    assert config.users[0].github_user == "octocat"
    assert config.users[0].recipient_email == "to@example.com"
    assert config.smtp is not None
    assert config.users[0].smtp is config.smtp
    assert config.smtp.host == "smtp.example.com"
    assert config.smtp.port == 587
    assert config.smtp.sender == "from@example.com"
    assert config.smtp.recipient == "to@example.com"
    assert config.smtp.subject == "Daily tasks"
    assert config.smtp.use_tls is True
    assert config.smtp.use_ssl is False


def test_load_config_rejects_invalid_output_format(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("DIGEST_OUTPUT_FORMAT", "pdf")

    with pytest.raises(ValueError, match="DIGEST_OUTPUT_FORMAT"):
        load_config()


def test_load_config_treats_github_user_without_email_as_stdout_only(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_USER", "octocat")

    config = load_config()

    assert config.github_user == "octocat"
    assert config.recipient_email is None
    assert len(config.users) == 1
    assert config.users[0].github_user == "octocat"
    assert config.users[0].recipient_email is None
    assert config.users[0].smtp is None
    assert config.smtp is None


def test_load_config_supports_empty_github_user_with_email(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_USER", ":to@example.com")
    _set_smtp_env(monkeypatch)

    config = load_config()

    assert config.github_user == "@me"
    assert config.recipient_email == "to@example.com"
    assert len(config.users) == 1
    assert config.users[0].github_user == "@me"
    assert config.users[0].recipient_email == "to@example.com"
    assert config.smtp is not None
    assert config.users[0].smtp is config.smtp


def test_load_config_parses_multiple_users_without_email(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_USER", "wesley-dean,joe-dean")

    config = load_config()

    assert [user.github_user for user in config.users] == ["wesley-dean", "joe-dean"]
    assert [user.recipient_email for user in config.users] == [None, None]
    assert [user.smtp for user in config.users] == [None, None]
    assert config.github_user == "wesley-dean"
    assert config.recipient_email is None
    assert config.smtp is None


def test_load_config_parses_multiple_users_with_email(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_USER", "wesley-dean:wes@example.com,joe-dean:joe@example.com")
    _set_smtp_env(monkeypatch)

    config = load_config()

    assert [user.github_user for user in config.users] == ["wesley-dean", "joe-dean"]
    assert [user.recipient_email for user in config.users] == ["wes@example.com", "joe@example.com"]
    assert all(user.smtp is not None for user in config.users)
    assert [user.smtp.recipient for user in config.users if user.smtp] == ["wes@example.com", "joe@example.com"]
    assert config.github_user == "wesley-dean"
    assert config.recipient_email == "wes@example.com"
    assert config.smtp is config.users[0].smtp


def test_load_config_parses_mixed_user_forms(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_USER", "@me,joe-dean:joe@example.com,octocat")
    _set_smtp_env(monkeypatch)

    config = load_config()

    assert [user.github_user for user in config.users] == ["@me", "joe-dean", "octocat"]
    assert [user.recipient_email for user in config.users] == [None, "joe@example.com", None]
    assert config.users[0].smtp is None
    assert config.users[1].smtp is not None
    assert config.users[1].smtp.recipient == "joe@example.com"
    assert config.users[2].smtp is None
    assert config.github_user == "@me"
    assert config.recipient_email is None
    assert config.smtp is None


def test_load_config_ignores_whitespace_around_user_entries(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_USER", " wesley-dean , joe-dean:joe@example.com , octocat ")
    _set_smtp_env(monkeypatch)

    config = load_config()

    assert [user.github_user for user in config.users] == ["wesley-dean", "joe-dean", "octocat"]
    assert [user.recipient_email for user in config.users] == [None, "joe@example.com", None]


@pytest.mark.parametrize(
    "github_user",
    [
        "wesley-dean,,joe-dean",
        ",wesley-dean",
        "wesley-dean,",
        "wesley-dean,   ,joe-dean",
    ],
)
def test_load_config_rejects_empty_user_entries(monkeypatch, tmp_path, github_user) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("GITHUB_USER", github_user)

    with pytest.raises(ValueError, match="GITHUB_USER contains an empty user entry"):
        load_config()


def test_load_config_ignores_shell_user(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("USER", "root")

    config = load_config()

    assert config.github_user == "@me"
    assert config.recipient_email is None
    assert len(config.users) == 1
    assert config.users[0].github_user == "@me"
    assert config.users[0].recipient_email is None


def test_load_config_accepts_github_app_auth_without_pat(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "67890")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "test-key-fixture")
    monkeypatch.setenv("GITHUB_PROJECT_OWNER", "wesley-dean")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "1")

    config = load_config()

    assert config.github_token is None
    assert config.github_app.app_id == "12345"
    assert config.github_app.installation_id == "67890"
    assert config.github_app.private_key is not None
    assert config.github_app.configured is True


def test_load_config_supports_output_format_alias(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("OUTPUT_FORMAT", "html")

    config = load_config()

    assert config.output_format == "html"


def test_load_config_reads_due_marker_thresholds(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("DUE_SOON_DAYS", "5")
    monkeypatch.setenv("DUE_UPCOMING_DAYS", "10")

    config = load_config()

    assert config.due_soon_days == 5
    assert config.due_upcoming_days == 10


def test_load_config_defaults_to_sending_empty_email(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)

    config = load_config()

    assert config.send_empty_email is DEFAULT_SEND_EMPTY_EMAIL
    assert config.send_empty_email is True


def test_load_config_reads_send_empty_email_true(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("SEND_EMPTY_EMAIL", "true")

    config = load_config()

    assert config.send_empty_email is True


def test_load_config_reads_send_empty_email_false(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("SEND_EMPTY_EMAIL", "false")

    config = load_config()

    assert config.send_empty_email is False


def test_load_config_rejects_invalid_send_empty_email(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("SEND_EMPTY_EMAIL", "maybe")

    with pytest.raises(ValueError, match="SEND_EMPTY_EMAIL"):
        load_config()


def test_load_config_rejects_negative_due_soon_days(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("DUE_SOON_DAYS", "-1")

    with pytest.raises(ValueError, match="DUE_SOON_DAYS"):
        load_config()


def test_load_config_rejects_upcoming_days_before_soon_days(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    _set_required_project_env(monkeypatch)
    monkeypatch.setenv("DUE_SOON_DAYS", "10")
    monkeypatch.setenv("DUE_UPCOMING_DAYS", "5")

    with pytest.raises(ValueError, match="DUE_UPCOMING_DAYS"):
        load_config()
