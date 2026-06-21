"""@file render.py
@brief Render digest data through Jinja2 templates.
@details
This module keeps presentation concerns inside templates while source code
handles the location of those templates and safe rendering defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_digest(template_name: str, context: dict[str, Any]) -> str:
    """@fn render_digest(template_name, context)
    @brief Render a digest template with the supplied context.
    @details
    The Jinja2 environment enables autoescaping for HTML-like templates and
    keeps template whitespace manageable for email output.

    @param template_name File name inside the templates directory.
    @param context Values made available to the template.
    @returns Rendered template output as a string.

    @par Examples
    @code
    output = render_digest("digest.txt.j2", context)
    @endcode
    """

    root = Path(__file__).resolve().parents[2]
    templates_dir = root / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    return template.render(**context)
