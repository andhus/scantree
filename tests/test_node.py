import pytest

from scantree import CyclicLinkedDir, DirNode, LinkedDir, RecursionPath
from scantree.test_utils import get_mock_recursion_path


def create_basic_entries(local_path):
    d1 = local_path.join("d1")
    d1.mkdir()
    f1 = local_path.join("f1")
    f1.write("file1")
    local_path.join("ld1").mksymlinkto(d1)
    local_path.join("lf1").mksymlinkto(f1)


class TestDirNode:
    test_class = DirNode

    def test_init(self):
        dn = self.test_class(RecursionPath.from_root("."), [], [None])
        assert dn.directories == (None,)
        assert dn.files == ()

    def test_empty(self):
        dn = self.test_class(RecursionPath.from_root("."), [], [])
        assert dn.empty

    def test_apply(self, tmpdir):
        create_basic_entries(tmpdir)
        root = RecursionPath.from_root(tmpdir)
        d1 = next(rp for rp in root.scandir() if rp.name == "d1")
        dn = self.test_class(
            path=root, directories=[self.test_class(d1, files=[1.0, 2.0])], files=[0.5]
        )
        dn_new = dn.apply(
            file_apply=lambda x: x * 2,
            dir_apply=lambda dn_: sum(dn_.directories) ** 2 + sum(dn_.files),
        )
        assert dn_new == ((2 + 4) ** 2 + 1)

    def test_leafpaths_filepaths(self):
        rp_file1 = get_mock_recursion_path("file1")
        rp_dir1 = get_mock_recursion_path("dir1")
        rp_file2 = get_mock_recursion_path("dir1/file2")
        rp_linked_dir = get_mock_recursion_path("linked_dir")
        rp_cyclic = get_mock_recursion_path("cyclic")
        rp_cyclic_target = get_mock_recursion_path("cyclic_target")

        ordered_leafpaths = [rp_cyclic, rp_file2, rp_file1, rp_linked_dir]
        ordered_filepaths = [rp_file2, rp_file1]

        tree = self.test_class(
            path=get_mock_recursion_path(""),
            files=[rp_file1],
            directories=[
                CyclicLinkedDir(path=rp_cyclic, target_path=rp_cyclic_target),
                self.test_class(path=rp_dir1, files=[rp_file2]),
                LinkedDir(path=rp_linked_dir),
            ],
        )
        assert tree.leafpaths() == ordered_leafpaths
        assert tree.filepaths() == ordered_filepaths

    def test_entries(self):
        dn = self.test_class(
            RecursionPath.from_root("."), files=[None], directories=["d1", "d2"]
        )
        assert dn.entries == dn.files + dn.directories


class TestLinkedDir:
    test_class = LinkedDir

    @staticmethod
    def get_default_kwargs():
        return {"path": get_mock_recursion_path("path/to/ld")}

    def test_undefined_attributes(self):
        ld = self.test_class(**self.get_default_kwargs())
        for attribute in ["files", "directories", "entries"]:
            with pytest.raises(AttributeError):
                getattr(ld, attribute)

    def test_empty(self):
        ld = self.test_class(**self.get_default_kwargs())
        with pytest.raises(AttributeError):
            ld.empty  # noqa

    def test_apply(self):
        ld = self.test_class(**self.get_default_kwargs())
        res = ld.apply(dir_apply=lambda x: (x, 1), file_apply=None)
        assert res == (ld, 1)


class TestCyclicLinkedDir(TestLinkedDir):
    test_class = CyclicLinkedDir

    @staticmethod
    def get_default_kwargs():
        return {
            "path": get_mock_recursion_path("path/to/ld"),
            "target_path": get_mock_recursion_path("target"),
        }

    def test_empty(self):
        cld = self.test_class(**self.get_default_kwargs())
        assert cld.empty is False
