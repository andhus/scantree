from os import scandir
from pathlib import Path

import pytest

from scantree import DirEntryReplacement
from scantree.compat import fspath
from scantree.test_utils import assert_dir_entry_equal


def create_basic_entries(local_path):
    d1 = local_path.join("d1")
    d1.mkdir()
    f1 = local_path.join("f1")
    f1.write("file1")
    local_path.join("ld1").mksymlinkto(d1)
    local_path.join("lf1").mksymlinkto(f1)


class TestDirEntryReplacement:
    test_class = DirEntryReplacement

    def test_equivalence(self, tmpdir):
        create_basic_entries(tmpdir)
        for de_true in scandir(tmpdir):
            de_rep_from_entry = self.test_class.from_dir_entry(de_true)
            de_rep_from_path = self.test_class.from_path(tmpdir.join(de_true.name))
            assert_dir_entry_equal(de_rep_from_entry, de_true)
            assert de_rep_from_entry == de_true
            assert_dir_entry_equal(de_rep_from_path, de_true)
            assert de_rep_from_path == de_true

            # test not equal
            de_rep = self.test_class.from_dir_entry(de_true)
            assert de_rep != "other type"

            for attribute in ["path", "name"]:
                de_rep = self.test_class.from_dir_entry(de_true)
                setattr(de_rep, attribute, "wrong value")
                assert de_rep != de_true

            for bool_attr in ["_is_dir", "_is_file", "_is_symlink"]:
                de_rep = self.test_class.from_dir_entry(de_true)
                assert de_rep == de_true  # must load cache values before negating
                setattr(de_rep, bool_attr, not getattr(de_rep, bool_attr))
                assert de_rep != de_true

            de_rep = self.test_class.from_dir_entry(de_true)
            assert de_rep == de_true
            de_rep._stat_sym = "wrong_value"
            assert de_rep != de_true

            de_rep = self.test_class.from_dir_entry(de_true)
            assert de_rep == de_true
            de_rep._stat_nosym = "wrong_value"
            assert de_rep != de_true

    def test_raise_on_not_exists(self, tmpdir):
        with pytest.raises(IOError):
            self.test_class.from_path(tmpdir.join("no such entry"))


class TestRecursionPath:
    from scantree import RecursionPath as test_class

    def test_from_root(self, tmpdir):
        create_basic_entries(tmpdir)
        rpath = self.test_class.from_root(tmpdir.realpath())
        assert rpath.root == rpath.real == tmpdir.realpath()
        assert rpath.relative == ""
        d1 = rpath._join(DirEntryReplacement.from_path(tmpdir.join("d1")))
        assert d1.relative == "d1"
        assert d1.real == tmpdir.join("d1").realpath()
        assert d1.root == rpath.root
        ld1 = rpath._join(DirEntryReplacement.from_path(tmpdir.join("ld1")))
        assert ld1.relative == "ld1"
        assert ld1.real == tmpdir.join("d1").realpath()
        assert d1.root == rpath.root

    def test_dir_entry_interface(self, tmpdir):
        create_basic_entries(tmpdir)
        for de_true in scandir(tmpdir):
            de_repl = DirEntryReplacement.from_path(de_true.path)
            rpath_from_de_true = self.test_class.from_root(de_true)
            rpath_from_de_repl = self.test_class.from_root(de_repl)
            rpath_from_path = self.test_class.from_root(de_true.path)
            assert_dir_entry_equal(de_true, rpath_from_de_true)
            assert_dir_entry_equal(de_true, rpath_from_de_repl)
            assert_dir_entry_equal(de_true, rpath_from_path)

    def test_scandir(self, tmpdir):
        create_basic_entries(tmpdir)
        rpath = self.test_class.from_root(tmpdir)
        sub_rpaths = list(rpath.scandir())
        sub_des = list(scandir(rpath))
        assert len(sub_rpaths) == len(sub_des)
        for sub_de, sub_rpath in zip(sub_des, sub_rpaths):
            assert_dir_entry_equal(sub_de, sub_rpath)

    def test_picklable(self, tmpdir):
        rpath = self.test_class.from_root(tmpdir)
        state = rpath.__getstate__()
        dir_entry = state[-1]
        assert isinstance(dir_entry, DirEntryReplacement)
        rpath.__setstate__(state)
        assert rpath._dir_entry is dir_entry

    def test_as_pathlib(self, tmpdir):
        rpath = self.test_class.from_root(tmpdir)
        pathlib_path = rpath.as_pathlib()
        assert isinstance(pathlib_path, Path)
        assert fspath(pathlib_path) == rpath.absolute
