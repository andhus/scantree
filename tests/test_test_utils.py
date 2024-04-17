import attr
import pytest

from scantree import DirEntryReplacement
from scantree.test_utils import assert_dir_entry_equal


class MockStat:
    def __init__(self, st_ino=None):
        self.st_ino = st_ino


class TestAssertDirEntryEqual:
    def get_mock_dir_entry(self):
        de = DirEntryReplacement(path="/path/to/mock", name="mock")
        de._is_dir = True
        de._is_file = False
        de._is_symlink = False
        de._stat_sym = MockStat(1)
        de._stat_nosym = MockStat(0)

        return de

    def test_equal(self):
        de = self.get_mock_dir_entry()
        assert_dir_entry_equal(de, de)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"path": "other/path"},
            {"name": "other_name"},
            {"_is_dir": False},
            {"_is_file": True},
            {"_is_symlink": True},
            {"_stat_sym": MockStat(11)},
            {"_stat_nosym": MockStat(22)},
        ],
    )
    def test_not_equal(self, kwargs):
        de = self.get_mock_dir_entry()
        de_different = attr.evolve(de)
        for k, v in kwargs.items():
            setattr(de_different, k, v)
        with pytest.raises(AssertionError):
            assert_dir_entry_equal(de, de_different)
