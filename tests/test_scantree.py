import os
import re
from functools import partial
from time import sleep, time

import pytest

from scantree import (
    CyclicLinkedDir,
    DirNode,
    LinkedDir,
    RecursionFilter,
    RecursionPath,
    SymlinkRecursionError,
    scantree,
)
from scantree.test_utils import assert_dir_node_equal


class TestScantree:
    def test_basic(self, tmpdir):
        tmpdir.ensure("root/f1")
        tmpdir.ensure("root/d1/f1")
        tmpdir.ensure("root/d1/d11/f1")
        tmpdir.ensure("root/d2/f1")
        root = tmpdir.join("root")

        tree = scantree(root)

        def rp(relative):
            recursion_path = RecursionPath.from_root(root.join(relative))
            recursion_path.relative = relative
            recursion_path.root = root.strpath

            return recursion_path

        tree_expected = DirNode(
            path=rp(""),
            files=[rp("f1")],
            directories=[
                DirNode(
                    path=rp("d1"),
                    files=[rp("d1/f1")],
                    directories=[DirNode(path=rp("d1/d11"), files=[rp("d1/d11/f1")])],
                ),
                DirNode(path=rp("d2"), files=[rp("d2/f1")]),
            ],
        )

        assert_dir_node_equal(tree, tree_expected)

    def test_not_a_directory(self, tmpdir):
        tmpdir.ensure("root/f1")
        # does not exist
        with pytest.raises(ValueError):
            scantree(tmpdir.join("wrong_root"))
        # is a file
        with pytest.raises(ValueError):
            scantree(tmpdir.join("root/f1"))

    @pytest.mark.parametrize("include_empty", [True, False])
    def test_cyclic_links(self, tmpdir, include_empty):
        root = tmpdir.join("root")
        d1 = root.join("d1")
        d1.ensure(dir=True)
        d1.join("link_back_d1").mksymlinkto(d1)
        d1.join("link_back_root").mksymlinkto(root)

        tree = scantree(root, include_empty=include_empty)

        def rp(relative):
            recursion_path = RecursionPath.from_root(root.join(relative))
            recursion_path.relative = relative
            recursion_path.root = root.strpath

            return recursion_path

        tree_expected = DirNode(
            path=rp(""),
            directories=[
                DirNode(
                    path=rp("d1"),
                    directories=[
                        CyclicLinkedDir(
                            path=rp("d1/link_back_d1"), target_path=rp("d1")
                        ),
                        CyclicLinkedDir(
                            path=rp("d1/link_back_root"), target_path=rp("")
                        ),
                    ],
                )
            ],
        )

        assert_dir_node_equal(tree, tree_expected)

        with pytest.raises(SymlinkRecursionError) as exc_info:
            scantree(root, allow_cyclic_links=False)

        assert re.match(
            re.compile(
                "Symlink recursion: Real path .*root/d1' "
                "was encountered at .*root/d1' "
                "and then .*root/d1/link_back_d1'."
            ),
            str(exc_info.value),
        )

    @pytest.mark.parametrize("include_empty", [True, False])
    def test_follow_links(self, tmpdir, include_empty):
        root = tmpdir.join("root")
        root.join("f1").ensure(dir=False)
        external_d1 = tmpdir.join("d1")
        external_d1.join("f2").ensure(dir=False)
        root.join("link_to_d1").mksymlinkto(external_d1)

        def rp(relative):
            recursion_path = RecursionPath.from_root(root.join(relative))
            recursion_path.relative = relative
            recursion_path.root = root.strpath

            return recursion_path

        tree_follow_false = scantree(
            root, include_empty=include_empty, follow_links=False
        )
        tree_follow_true = scantree(
            root, include_empty=include_empty, follow_links=True
        )
        tree_follow_false_expected = DirNode(
            path=rp(""),
            files=[rp("f1")],
            directories=[LinkedDir(path=rp("link_to_d1"))],
        )
        tree_follow_true_expected = DirNode(
            path=rp(""),
            files=[rp("f1")],
            directories=[DirNode(path=rp("link_to_d1"), files=[rp("link_to_d1/f2")])],
        )
        assert_dir_node_equal(tree_follow_false, tree_follow_false_expected)
        assert_dir_node_equal(tree_follow_true, tree_follow_true_expected)

    def test_include_empty(self, tmpdir):
        root = tmpdir.join("root")
        root.join("d1").ensure(dir=True)

        tree_empty_true = scantree(root, include_empty=True)

        def rp(relative):
            recursion_path = RecursionPath.from_root(root.join(relative))
            recursion_path.relative = relative
            recursion_path.root = root.strpath

            return recursion_path

        tree_empty_true_expected = DirNode(
            path=rp(""), directories=[DirNode(path=rp("d1"))]
        )

        assert_dir_node_equal(tree_empty_true, tree_empty_true_expected)

        tree_empty_false = scantree(root, include_empty=False)
        tree_empty_false_expected = DirNode(path=rp(""))
        assert tree_empty_false == tree_empty_false_expected

    def test_multiprocess_speedup(self, tmpdir):
        num_files = 4
        for i in range(num_files):
            tmpdir.join(f"file_{i}").ensure()

        wait_time = 0.5
        expected_min_elapsed = wait_time * num_files
        slow_file_apply = get_slow_identity_f(wait_time)
        start = time()
        scantree(tmpdir, file_apply=slow_file_apply)
        end = time()
        elapsed_sequential = end - start
        assert elapsed_sequential > expected_min_elapsed

        start = time()
        scantree(tmpdir, file_apply=slow_file_apply, jobs=num_files)
        end = time()
        elapsed_muliproc = end - start
        assert elapsed_muliproc < expected_min_elapsed / 2
        # just require at least half to account for multiprocessing overhead

    def test_cache_by_real_path_speedup(self, tmpdir):
        target_file = tmpdir.join("target_file")
        target_file.ensure()
        num_links = 10
        for i in range(num_links):
            tmpdir.join(f"link_{i}").mksymlinkto(target_file)

        wait_time = 0.1
        expected_min_elapsed = wait_time * (num_links + 1)
        slow_file_apply = get_slow_identity_f(wait_time)
        start = time()
        scantree(tmpdir, file_apply=slow_file_apply)
        end = time()
        elapsed_sequential = end - start
        assert elapsed_sequential > expected_min_elapsed
        overhead = elapsed_sequential - expected_min_elapsed

        overhead_margin_factor = 1.5
        expected_max_elapsed = overhead * overhead_margin_factor + wait_time
        assert expected_max_elapsed < expected_min_elapsed
        start = time()
        scantree(tmpdir, file_apply=slow_file_apply, cache_file_apply=True)
        end = time()
        elapsed_cache = end - start
        assert elapsed_cache < expected_max_elapsed

    def test_cache_together_with_multiprocess_speedup(self, tmpdir):
        target_file_names = ["target_file_1", "target_file_2"]
        num_links_per_file = 10
        for i, target_file_name in enumerate(target_file_names):
            target_file = tmpdir.join(target_file_name)
            target_file.ensure()
            for j in range(num_links_per_file):
                tmpdir.join(f"link_{i}_{j}").mksymlinkto(target_file)
        num_links = num_links_per_file * len(target_file_names)

        wait_time = 0.1
        jobs = 2
        expected_min_elapsed = (wait_time * (num_links + len(target_file_names))) / jobs
        slow_file_apply = get_slow_identity_f(wait_time)
        start = time()
        scantree(tmpdir, file_apply=slow_file_apply, jobs=2)
        end = time()
        elapsed_mp = end - start
        assert elapsed_mp > expected_min_elapsed
        overhead = elapsed_mp - expected_min_elapsed

        overhead_margin_factor = 1.5
        expected_max_elapsed = overhead * overhead_margin_factor + wait_time * 2
        assert expected_max_elapsed < expected_min_elapsed
        start = time()
        scantree(tmpdir, file_apply=slow_file_apply, cache_file_apply=True, jobs=2)
        end = time()
        elapsed_mp_cache = end - start
        assert elapsed_mp_cache < expected_max_elapsed


def _slow_identity(x, wait_time):
    sleep(wait_time)
    return x


def get_slow_identity_f(wait_time):
    return partial(_slow_identity, wait_time=wait_time)


class TestIncludedPaths:
    """Verify included leafpaths given combinations of options"""

    @staticmethod
    def get_leafpaths(directory, **kwargs):
        """Extract relative paths to leafs (with extra "/." for directories)"""
        return [
            path.relative if path.is_file() else os.path.join(path.relative, ".")
            for path in scantree(directory, **kwargs).leafpaths()
        ]

    def test_basic(self, tmpdir):
        tmpdir.ensure("root/f1")
        tmpdir.ensure("root/d1/f1")
        tmpdir.ensure("root/d1/d11/f1")
        tmpdir.ensure("root/d2/f1")

        expected_filepaths = ["d1/d11/f1", "d1/f1", "d2/f1", "f1"]
        filepaths = self.get_leafpaths(tmpdir.join("root"))
        assert filepaths == expected_filepaths

        # test pure string path as well
        filepaths = self.get_leafpaths(tmpdir.join("root").strpath)
        assert filepaths == expected_filepaths

    def test_symlinked_file(self, tmpdir):
        tmpdir.ensure("root/f1")
        tmpdir.ensure("linked_file")
        tmpdir.join("root/f2").mksymlinkto(tmpdir.join("linked_file"))
        root = tmpdir.join("root")

        # NOTE `follow_links` has no effect if linked files are included
        filepaths = self.get_leafpaths(root, follow_links=False)
        assert filepaths == ["f1", "f2"]

        filepaths = self.get_leafpaths(root, follow_links=True)
        assert filepaths == ["f1", "f2"]

        filepaths = self.get_leafpaths(
            root,
            recursion_filter=RecursionFilter(linked_files=False),
        )
        assert filepaths == ["f1"]

    def test_symlinked_dir(self, tmpdir):
        tmpdir.ensure("root/f1")
        tmpdir.ensure("linked_dir/f1")
        tmpdir.ensure("linked_dir/f2")
        tmpdir.join("root/d1").mksymlinkto(tmpdir.join("linked_dir"))
        root = tmpdir.join("root")

        filepaths = self.get_leafpaths(root, follow_links=True)
        assert filepaths == ["d1/f1", "d1/f2", "f1"]

        # default is `follow_links=True`
        filepaths = self.get_leafpaths(root)
        assert filepaths == ["d1/f1", "d1/f2", "f1"]

        filepaths = self.get_leafpaths(root, follow_links=False)
        assert filepaths == ["d1/.", "f1"]

        # correct way to ignore linked dirs completely:
        filepaths = self.get_leafpaths(
            root,
            recursion_filter=RecursionFilter(linked_dirs=False),
        )
        assert filepaths == ["f1"]
