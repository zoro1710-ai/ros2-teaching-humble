"""Docstring convention check, run automatically by colcon test."""

from ament_pep257.main import main
import pytest


@pytest.mark.linter
@pytest.mark.pep257
def test_pep257():
    """Fail if pep257 reports any issue."""
    rc = main(argv=['.', 'test'])
    assert rc == 0, 'Found code style errors / warnings'
