"""TOML template parser."""
from pathlib import Path
from typing import Union

import toml
from pydantic import ValidationError

from bsie.templates.schema import Template


class TemplateParseError(Exception):
    """Error parsing template."""
    pass


def parse_template(source: Union[str, Path]) -> Template:
    """
    Parse a template from TOML string or file path.

    Args:
        source: TOML string or path to TOML file

    Returns:
        Validated Template object

    Raises:
        TemplateParseError: If parsing or validation fails
    """
    try:
        if isinstance(source, Path):
            with open(source, "r") as f:
                data = toml.load(f)
        else:
            data = toml.loads(source)
    except toml.TomlDecodeError as e:
        raise TemplateParseError(f"Invalid TOML: {e}") from e

    try:
        return Template.model_validate(data)
    except ValidationError as e:
        raise TemplateParseError(f"Template validation failed: {e}") from e
