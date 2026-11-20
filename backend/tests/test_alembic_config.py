from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_has_single_head() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1


def test_initial_migration_is_root() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    revision = script.get_revision("20261118_0001")
    assert revision is not None
    assert revision.down_revision is None


def test_migration_directory_exists() -> None:
    assert Path("alembic/versions").is_dir()
