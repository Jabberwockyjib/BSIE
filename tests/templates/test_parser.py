"""Template parser tests."""
import pytest
from pathlib import Path

from bsie.templates.parser import parse_template, TemplateParseError


def test_parse_template_from_string():
    toml_content = '''
[metadata]
template_id = "test_checking_v1"
version = "1.0.0"
bank_family = "test_bank"
statement_type = "checking"
segment = "personal"

[detect]
keywords = ["TEST BANK"]
required_text = ["Account Activity"]
'''
    template = parse_template(toml_content)
    assert template.metadata.template_id == "test_checking_v1"
    assert template.metadata.bank_family == "test_bank"
    assert "TEST BANK" in template.detect.keywords


def test_parse_template_missing_metadata():
    toml_content = '''
[detect]
keywords = ["TEST"]
'''
    with pytest.raises(TemplateParseError) as exc:
        parse_template(toml_content)
    assert "metadata" in str(exc.value).lower()


def test_parse_template_from_file(tmp_path):
    template_file = tmp_path / "test.toml"
    template_file.write_text('''
[metadata]
template_id = "file_test_v1"
version = "1.0.0"
bank_family = "test"
statement_type = "checking"
segment = "personal"

[detect]
keywords = ["TEST"]
''')
    template = parse_template(template_file)
    assert template.metadata.template_id == "file_test_v1"
