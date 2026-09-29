"""Docstring check run automatically by `colcon test`."""

from ament_pep257.main import main
import pytest


@pytest.mark.linter
@pytest.mark.pep257
def test_pep257():
    """Fail if any docstring violates the ament pep257 conventions."""
    rc = main(argv=['.', 'test'])
    assert rc == 0, 'Found code style errors / warnings'
