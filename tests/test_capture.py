import importlib
from importlib.metadata import requires

import pytest
from typer.testing import CliRunner

from quick_capture.config import AppConfig
from quick_capture.writer import CaptureWriter


def test_installed_package_declares_settings_dependency():
    dependencies = requires("quick-capture") or []
    assert any(dependency.startswith("pydantic-settings>=") for dependency in dependencies)


@pytest.fixture
def config(tmp_path):
    return AppConfig(vault_path=tmp_path / "graph", _env_file=None)


@pytest.mark.parametrize("capture_type", ["typo", "TASK", "", "notes"])
def test_writer_rejects_invalid_type_without_writes(config, capture_type):
    with pytest.raises(ValueError, match="Invalid capture type"):
        CaptureWriter(config).capture("synthetic", capture_type, date_str="2026-10-29")
    assert not config.daily_notes_path.exists()


@pytest.mark.parametrize("date", ["", "2026-1-2", "2026-10-9", "2026-02-30"])
def test_invalid_date_never_writes(config, date):
    with pytest.raises(ValueError):
        CaptureWriter(config).capture("synthetic", date_str=date)
    assert not config.daily_notes_path.exists()


@pytest.mark.parametrize("date", ["", "2026-1-2", "2026-02-30"])
def test_cli_rejects_invalid_date(config, monkeypatch, date):
    main = importlib.import_module("quick_capture.main")
    monkeypatch.setattr(main, "load_config", lambda: config)
    result = CliRunner().invoke(main.app, ["capture", "synthetic", "--date", date])
    assert result.exit_code == 1
    assert not config.daily_notes_path.exists()


def test_cli_rejects_invalid_type(config, monkeypatch):
    main = importlib.import_module("quick_capture.main")
    monkeypatch.setattr(main, "load_config", lambda: config)
    result = CliRunner().invoke(main.app, ["capture", "synthetic", "--type", "typo"])
    assert result.exit_code == 1
    assert not config.daily_notes_path.exists()


@pytest.mark.parametrize("kwargs", [{"capture_type": "typo"}, {"date_str": ""}])
def test_invalid_inputs_preserve_existing_journal(config, kwargs):
    path = config.get_today_note_path()
    path.parent.mkdir(parents=True)
    original = "## Notes\r\n- synthetic café\r\n".encode()
    path.write_bytes(original)
    with pytest.raises(ValueError):
        CaptureWriter(config).capture("must not appear", **kwargs)
    assert path.read_bytes() == original
    assert sorted(p.name for p in path.parent.iterdir()) == [path.name]


@pytest.mark.parametrize("capture_type", ["task", "idea", "note", "log"])
def test_valid_capture_types_and_leap_day(config, capture_type):
    path, entry = CaptureWriter(config).capture("café", capture_type, date_str="2024-02-29")
    assert path.name == "2024-02-29.md"
    assert entry in path.read_text(encoding="utf-8")
    assert "café" in entry


@pytest.mark.parametrize("section", ["Notes", "Custom"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_appends_after_section_blocks_preserving_other_content(config, section, newline):
    original = (
        f"# Synthetic\n\n## {section} archive\n- untouched\n\n"
        f"## {section}\n- parent café\n  - child\n### Detail\n- detail\n\n"
        "## Links\n- [[preserve]]\n\n"
    ).replace("\n", newline)
    path = config.get_today_note_path("2026-10-29")
    path.parent.mkdir(parents=True)
    path.write_bytes(original.encode())
    _, entry = CaptureWriter(config).capture("new", section=section, date_str="2026-10-29")
    expected = original.replace(f"- detail{newline}", f"- detail{newline}{entry}{newline}")
    assert path.read_bytes() == expected.encode()


def test_missing_section_preserves_trailing_content(config):
    writer = CaptureWriter(config)
    original = "## Links\n- café  \n\n\n"
    result = writer._insert_in_section(original, "- new", "Custom")
    assert result.startswith(original)
    assert "## Custom\n\n- new" in result


@pytest.mark.parametrize("body", ["", "- first\n  - child\n", "- café"])
def test_exact_section_boundary_and_no_final_newline(config, body):
    writer = CaptureWriter(config)
    original = "## Notes\n" + body
    result = writer._insert_in_section(original, "- new", "Notes")
    prefix = original if original.endswith("\n") else original + "\n"
    assert result == prefix + "- new\n"


def test_existing_section_keeps_children_and_following_section(config):
    writer = CaptureWriter(config)
    original = "## Notes\n- parent\n  - child\n\n## Links\n- keep\n"
    assert writer._insert_in_section(original, "- new", "Notes") == (
        "## Notes\n- parent\n  - child\n- new\n\n## Links\n- keep\n"
    )


def test_unreadable_journal_is_not_overwritten(config):
    path = config.get_today_note_path("2026-10-29")
    path.parent.mkdir(parents=True)
    original = b"## Notes\n\xff\n"
    path.write_bytes(original)
    with pytest.raises(UnicodeDecodeError):
        CaptureWriter(config).capture("synthetic", date_str="2026-10-29")
    assert path.read_bytes() == original


def test_concurrent_captures_keep_every_entry(config):
    from concurrent.futures import ThreadPoolExecutor

    writer = CaptureWriter(config)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda i: writer.capture(f"synthetic-{i}", date_str="2026-10-29"), range(12))
        )
    content = results[0][0].read_text(encoding="utf-8")
    for _, entry in results:
        assert content.count(entry + "\n") == 1


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("fence", ["```", "~~~~", "`````"])
def test_fenced_fake_target_and_boundary_do_not_receive_capture(config, newline, fence):
    original = (
        f"{fence}markdown\n## Notes\n- fake target\n{fence}\n\n"
        f"## Notes ##\n- parent\n{fence}\n## Links\n- code\n{fence}\n"
        "- last real block\n\n## Links ##\n- untouched\n"
    ).replace("\n", newline)
    path = config.get_today_note_path("2026-10-29")
    path.parent.mkdir(parents=True)
    path.write_bytes(original.encode())
    _, entry = CaptureWriter(config).capture("new", date_str="2026-10-29")
    expected = original.replace(
        f"- last real block{newline}", f"- last real block{newline}{entry}{newline}"
    )
    assert path.read_bytes() == expected.encode()


@pytest.mark.parametrize("section", ["Notes", "Custom"])
def test_atx_closing_hashes_match_exact_section_only(config, section):
    original = f"## {section}Extra ##\n- keep\n## {section} ###  \n- old\n## Links\n"
    expected = original.replace("- old\n", "- old\n- new\n")
    assert CaptureWriter(config)._insert_in_section(original, "- new", section) == expected


@pytest.mark.parametrize(
    "fence,wrong,close",
    [
        ("````", "```", "`````"),
        ("~~~~", "~~~", "~~~~~"),
        ("```", "~~~", "```"),
        ("~~~", "```", "~~~"),
        ("```", "``` not closing", "```"),
    ],
)
def test_only_matching_fence_of_sufficient_length_closes(config, fence, wrong, close):
    original = (
        f"## Notes\n{fence}\n{wrong}\n## Links\n- code\n{close}\n"
        "- after code\n## Links\n- keep\n"
    )
    expected = original.replace("- after code\n", "- after code\n- new\n")
    assert CaptureWriter(config)._insert_in_section(original, "- new", "Notes") == expected


def test_short_fences_are_not_code_blocks(config):
    original = "``\n## Notes\n- old\n~~\n## Links\n- keep\n"
    expected = original.replace("~~\n", "~~\n- new\n")
    assert CaptureWriter(config)._insert_in_section(original, "- new", "Notes") == expected


@pytest.mark.parametrize("indent", ["", "   "])
@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_fenced_target_without_real_target_creates_section_outside_code(config, indent, fence):
    original = f"{indent}{fence}\n## Notes\n- code\n{indent}{fence}\n\n"
    expected = original + "## Notes\n\n- new\n"
    assert CaptureWriter(config)._insert_in_section(original, "- new", "Notes") == expected


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_unclosed_fence_refuses_capture_without_altering_journal(config, newline):
    path = config.get_today_note_path("2026-10-29")
    path.parent.mkdir(parents=True)
    original = "## Notes\n- café\n```\n## Links\n".replace("\n", newline).encode()
    path.write_bytes(original)
    with pytest.raises(ValueError, match="unclosed code fence"):
        CaptureWriter(config).capture("new", date_str="2026-10-29")
    assert path.read_bytes() == original
