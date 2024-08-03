import os

from ._node import CyclicLinkedDir, LinkedDir
from ._path import DirEntryReplacement, RecursionPath


def convert_path(path: str) -> str:
    if os.name == "nt":  # pragma: no cover
        # Windows uses backslashes
        return path.replace("/", "\\")
    else:
        # Most other systems use slashes
        return path.replace("\\", "/")


def assert_dir_entry_equal(de1, de2):
    # TODO check has attributes
    assert de1.path == de2.path
    assert de1.name == de2.name

    methods = [
        ("is_dir", {"follow_symlinks": True}),
        ("is_dir", {"follow_symlinks": False}),
        ("is_file", {"follow_symlinks": True}),
        ("is_file", {"follow_symlinks": False}),
        ("is_symlink", {}),
    ]
    if os.name != "nt":  # pragma: no cover
        methods.extend(
            [
                ("stat", {"follow_symlinks": True}),
                ("stat", {"follow_symlinks": False}),
                ("inode", {}),
            ]
        )

    for method, kwargs in methods:
        for attempt in [1, 2]:  # done two times to verify caching!
            res1 = getattr(de1, method)(**kwargs)
            res2 = getattr(de2, method)(**kwargs)
            if not res1 == res2:
                raise AssertionError(
                    f"\nde1.{method}(**{kwargs}) == {res1} != "
                    f"\nde2.{method}(**{kwargs}) == {res2} "
                    f"\n(attempt: {attempt})"
                    f"\nde1: {de1}"
                    f"\nde2: {de2}"
                )


def assert_recursion_path_equal(p1, p2):
    assert p1.root == p2.root
    assert p1.relative == convert_path(p2.relative)
    assert p1.real == p2.real
    assert p1.absolute == convert_path(p2.absolute)
    assert_dir_entry_equal(p1, p2)


def assert_dir_node_equal(dn1, dn2):
    assert_recursion_path_equal(dn1.path, dn2.path)
    if isinstance(dn1, LinkedDir):
        assert isinstance(dn2, LinkedDir)
    elif isinstance(dn1, CyclicLinkedDir):
        assert isinstance(dn2, CyclicLinkedDir)
        assert_recursion_path_equal(dn1.target_path, dn2.target_path)
    else:
        for path1, path2 in zip(dn1.files, dn2.files):
            assert_recursion_path_equal(path1, path2)
        for sub_dn1, sub_dn2 in zip(dn1.directories, dn2.directories):
            assert_dir_node_equal(sub_dn1, sub_dn2)


def get_mock_recursion_path(relative, root=None, is_dir=False, is_symlink=False):
    dir_entry = DirEntryReplacement(path=relative, name=os.path.basename(relative))
    dir_entry._is_dir = is_dir
    dir_entry._is_file = not is_dir
    dir_entry._is_symlink = is_symlink
    return RecursionPath(root=root, relative=relative, real=None, dir_entry=dir_entry)
