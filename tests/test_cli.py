from __future__ import annotations

from github_project_digest import cli
from github_project_digest.config import Config, ConfiguredUser
from github_project_digest.emailer import SmtpConfig
from github_project_digest.github_auth import GitHubAppConfig


def _smtp_config(recipient: str = "wesley-dean@example.com") -> SmtpConfig:
    return SmtpConfig(
        host="smtp.example.com",
        port=587,
        sender="digest@example.com",
        recipient=recipient,
        subject="GitHub Project Digest",
    )


def _config(output_format: str = "text", send_empty_email: bool = True) -> Config:
    user = ConfiguredUser("wesley-dean", None, None)
    return Config(
        github_token="value",
        github_app=GitHubAppConfig(),
        project_owner="wesley-dean",
        project_number=1,
        project_owner_type="user",
        users=[user],
        github_user=user.github_user,
        recipient_email=user.recipient_email,
        filter_query="state:open",
        output_format=output_format,
        text_template="digest.txt.j2",
        html_template="digest.html.j2",
        page_size=50,
        field_value_limit=50,
        due_soon_days=2,
        due_upcoming_days=7,
        send_empty_email=send_empty_email,
        smtp=None,
    )


def test_stdout_payload_preserves_single_user_text_output() -> None:
    config = _config()
    contexts = [{"requested_user": "wesley-dean"}]
    rendered_outputs = [{"text": "plain digest", "html": "html digest"}]

    assert cli._stdout_payload(config, contexts, rendered_outputs) == "plain digest"


def test_stdout_payload_separates_multiple_text_digests() -> None:
    config = _config()
    contexts = [{"requested_user": "wesley-dean"}, {"requested_user": "joe-dean"}]
    rendered_outputs = [
        {"text": "first digest", "html": "first html"},
        {"text": "second digest", "html": "second html"},
    ]

    output = cli._stdout_payload(config, contexts, rendered_outputs)

    assert "===== Digest for wesley-dean =====" in output
    assert "first digest" in output
    assert "===== Digest for joe-dean =====" in output
    assert "second digest" in output


def test_stdout_payload_wraps_multiple_json_digests() -> None:
    config = _config(output_format="json")
    contexts = [{"requested_user": "wesley-dean"}, {"requested_user": "joe-dean"}]
    rendered_outputs = [{"text": "first", "html": "first"}, {"text": "second", "html": "second"}]

    output = cli._stdout_payload(config, contexts, rendered_outputs)

    assert '"digests"' in output
    assert '"requested_user": "wesley-dean"' in output
    assert '"requested_user": "joe-dean"' in output


def test_stdout_payload_wraps_multiple_yaml_digests() -> None:
    config = _config(output_format="yaml")
    contexts = [{"requested_user": "wesley-dean"}, {"requested_user": "joe-dean"}]
    rendered_outputs = [{"text": "first", "html": "first"}, {"text": "second", "html": "second"}]

    output = cli._stdout_payload(config, contexts, rendered_outputs)

    assert "digests:" in output
    assert "requested_user: wesley-dean" in output
    assert "requested_user: joe-dean" in output


def test_should_deliver_user_digest_without_smtp_returns_false() -> None:
    config = _config()
    configured_user = ConfiguredUser("wesley-dean", None, None)
    context = {"count": 1}

    assert cli._should_deliver_user_digest(config, configured_user, context) is False


def test_should_deliver_user_digest_with_non_empty_digest_returns_true() -> None:
    config = _config(send_empty_email=False)
    smtp = _smtp_config()
    configured_user = ConfiguredUser("wesley-dean", smtp.recipient, smtp)
    context = {"count": 1}

    assert cli._should_deliver_user_digest(config, configured_user, context) is True


def test_should_deliver_user_digest_with_empty_digest_and_send_empty_true_returns_true() -> None:
    config = _config(send_empty_email=True)
    smtp = _smtp_config()
    configured_user = ConfiguredUser("wesley-dean", smtp.recipient, smtp)
    context = {"count": 0}

    assert cli._should_deliver_user_digest(config, configured_user, context) is True


def test_should_deliver_user_digest_with_empty_digest_and_send_empty_false_returns_false() -> None:
    config = _config(send_empty_email=False)
    smtp = _smtp_config()
    configured_user = ConfiguredUser("wesley-dean", smtp.recipient, smtp)
    context = {"count": 0}

    assert cli._should_deliver_user_digest(config, configured_user, context) is False
