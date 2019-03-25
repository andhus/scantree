from __future__ import print_function, division

import os

from multiprocessing.pool import Pool

from pathspec import RecursionError as _RecursionError

from .compat import fspath
from ._node import DirNode, LinkedDir, CyclicLinkedDir, identity, _is_empty_dir_node
from ._path import RecursionPath, DirEntryReplacement
from ._filter import RecursionFilter


def scantree(
    directory,
    recursion_filter=identity,
    file_apply=identity,
    dir_apply=identity,
    follow_links=True,
    allow_cyclic_links=True,
    cache_file_apply=False,
    include_empty=False,
    jobs=1
):
    _verify_is_directory(directory)

    if jobs is None or jobs > 1:
        return _scantree_multiprocess(**vars())

    path = RecursionPath.from_root(directory)

    if cache_file_apply:
        file_apply = _cached_by_realpath(file_apply)

    root_dir_node = _traverse_recursive(
        path=path,
        filter_=recursion_filter,
        file_apply=file_apply,
        dir_apply=dir_apply,
        follow_links=follow_links,
        allow_cyclic_links=allow_cyclic_links,
        include_empty=include_empty,
        parents={path.real: path},
    )

    result = dir_apply(root_dir_node)

    return result


def _scantree_multiprocess(**kwargs):
    file_apply = kwargs.pop('file_apply')
    dir_apply = kwargs.pop('dir_apply')
    jobs = kwargs.pop('jobs')

    file_paths = []

    def extract_paths(path):
        result_idx = len(file_paths)
        file_paths.append(path)
        return result_idx

    root_dir_node = scantree(file_apply=extract_paths, dir_apply=identity, **kwargs)

    pool = Pool(jobs)
    try:
        file_results = pool.map(file_apply, file_paths)
    finally:
        pool.close()

    def fetch_result(result_idx):
        return file_results[result_idx]

    return root_dir_node.apply(dir_apply=dir_apply, file_apply=fetch_result)


def _verify_is_directory(directory):
    directory = fspath(directory)
    if not os.path.exists(directory):
        raise ValueError('{}: No such directory'.format(directory))
    if not os.path.isdir(directory):
        raise ValueError('{}: Is not a directory'.format(directory))


def _cached_by_realpath(file_apply):
    cache = {}

    def file_apply_cached(path):
        if path.real not in cache:
            cache[path.real] = file_apply(path)
        return cache[path.real]

    return file_apply_cached


def _traverse_recursive(
    path,
    filter_,
    file_apply,
    dir_apply,
    follow_links,
    allow_cyclic_links,
    include_empty,
    parents,
):
    """TODO"""
    fwd_kwargs = vars()
    del fwd_kwargs['path']

    if path.is_symlink():
        if not follow_links:
            return LinkedDir(path)
        previous_path = parents.get(path.real, None)
        if previous_path is not None:
            if allow_cyclic_links:
                return CyclicLinkedDir(path, previous_path)
            else:
                raise SymlinkRecursionError(path, previous_path)

    if follow_links:
        parents[path.real] = path

    dirs = []
    files = []
    for subpath in sorted(filter_(path.scandir())):
        if subpath.is_dir():
            dir_node = _traverse_recursive(subpath, **fwd_kwargs)
            if include_empty or not _is_empty_dir_node(dir_node):
                dirs.append(dir_apply(dir_node))
        if subpath.is_file():
            files.append(file_apply(subpath))

    if follow_links:
        del parents[path.real]

    return DirNode(path=path, directories=dirs, files=files)


class SymlinkRecursionError(_RecursionError):
    """Raised when symlinks cause a cyclic graph of directories.

    Extends the `pathspec.util.RecursionError` but with a different name (avoid
    overriding the built-in error!) and with a more informative string representation
    (used in `dirhash.cli`).
    """
    def __init__(self, path, target_path):
        super(SymlinkRecursionError, self).__init__(
            real_path=path.real,
            first_path=os.path.join(target_path.root, target_path.relative),
            second_path=os.path.join(path.root, path.relative)
        )

    def __str__(self):
        # _RecursionError.__str__ prints args without context
        return 'Symlink recursion: {}'.format(self.message)
