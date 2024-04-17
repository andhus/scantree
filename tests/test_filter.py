import pytest

from scantree.test_utils import get_mock_recursion_path


class TestRecursionFilterBase:
    from scantree import RecursionFilter as test_class

    @pytest.mark.parametrize(
        "description, filter_kwargs, expected_output",
        [
            (
                "include all",
                {"linked_dirs": True, "linked_files": True},
                ["dir", "dir/file.txt", "ldir", "dir/lfile"],
            ),
            ("default include all", {}, ["dir", "dir/file.txt", "ldir", "dir/lfile"]),
            (
                "exclude linked dirs",
                {"linked_dirs": False, "linked_files": True},
                ["dir", "dir/file.txt", "dir/lfile"],
            ),
            (
                "exclude linked files",
                {"linked_dirs": True, "linked_files": False},
                ["dir", "dir/file.txt", "ldir"],
            ),
            (
                "exclude linked files and dirs",
                {"linked_dirs": False, "linked_files": False},
                ["dir", "dir/file.txt"],
            ),
            (
                "include only .txt files (dirs always included)",
                {"match": ["*.txt"]},
                ["dir", "dir/file.txt", "ldir"],
            ),
            (
                "exclude .txt files (dirs always included)",
                {"match": ["*", "!*.txt"]},
                ["dir", "ldir", "dir/lfile"],
            ),
        ],
    )
    def test_call(self, description, filter_kwargs, expected_output):
        paths = [
            get_mock_recursion_path("dir", is_dir=True),
            get_mock_recursion_path("dir/file.txt"),
            get_mock_recursion_path("ldir", is_dir=True, is_symlink=True),
            get_mock_recursion_path("dir/lfile", is_symlink=True),
        ]
        relpath_to_path = {path.relative: path for path in paths}
        rfilter = self.test_class(**filter_kwargs)
        filtered_paths = list(rfilter(paths))
        assert filtered_paths == [
            relpath_to_path[relpath] for relpath in expected_output
        ]
