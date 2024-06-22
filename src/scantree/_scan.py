import os
from multiprocessing.pool import Pool

from pathspec import RecursionError as _RecursionError

from ._node import CyclicLinkedDir, DirNode, LinkedDir, identity, is_empty_dir_node
from ._path import RecursionPath
from .compat import fspath


def scantree(
    directory,
    recursion_filter=identity,
    file_apply=identity,
    dir_apply=identity,
    follow_links=True,
    allow_cyclic_links=True,
    cache_file_apply=False,
    include_empty=False,
    jobs=1,
):
    """Recursively scan the file tree under the given directory.

    The files and subdirectories in each directory will be used to initialize a
    the object: `DirNode(path=..., files=[...], directories=[...])`, where `path`
    is the `RecursionPath` to the directory (relative to the root directory of the
    recursion), `files` is a list of the results of `file_apply` called on the
    recursion path of each file, and `directories` is a list of the results of
    `dir_apply` called on each `DirNode` obtained (recursively) for each
    subdirectory.
        Hence, with the default value (identity function) for `file_apply` and
    `dir_apply`, a tree-like data structure is returned representing the file tree
    of the scanned directory, with all relevant metadata *cached in memory*.

    This example illustrates the core concepts:

    ```
    >>> tree = scantree('/path/to/dir')
    >>> tree.directories[0].directories[0].path.absolute
    '/path/to/dir/sub_dir_0/sub_sub_dir_0'
    >>> tree.directories[0].directories[0].path.relative
    'sub_dir_0/sub_sub_dir_0'
    >>> tree.directories[0].files[0].relative
    'sub_dir_0/file_0'
    >>> tree.directories[0].path.real
    '/path/to/linked_dir/'
    >>> tree.directories[0].path.is_symlink()  # already cached, no OS call needed
    True
    ```

    By providing a different `dir_apply` and `file_apply` function, you can operate
    on the paths and/or data of files while scanning the directory recursively. If
    `dir_apply` returns some aggregate or nothing (i.e. `None`) the full tree will
    never be stored in memory. The same result can be obtained by calling
    `tree.apply(dir_apply=..., file_apply=...)` but this can be done repeatedly
    without having to rerun expensive OS calls.


    # Arguments:
        directory (str | os.PathLike): The directory to scan.
        recursion_filter (f: f([RecursionPath]) -> [RecursionPath]): A filter
            function, defining which files to include and which subdirectories to
            scan, e.g. an instance of `scantree.RecursionFilter`.
            The `RecursionPath` implements the os-portable `DirEntry` interface.
            It caches metadata efficiently and, in addition to
            DirEntry, provides real path and path relative to the root directory for
            the recursion as properties, see `scantree.RecursionPath` for further
            details.
        file_apply (f: f(RecursionPath) -> object): The function to apply to the
            `RecursionPath` for each file. Default "identity", i.e. `lambda x: x`.
        dir_apply (f: f(DirNode) -> object): The function to apply to the `DirNode`
            for each (sub) directory. Default "identity", i.e. `lambda x: x`.
        follow_links (bool): Whether to follow symbolic links for not, i.e. to
            continue the recursive scanning in linked directories. If False, linked
            directories are represented by the `LinkedDir` object which does e.g.
            not have the `files` and `directories` properties (as these cannot be
            known without following the link). Default `True`.
        allow_cyclic_links (bool): If set to `False`, a `SymlinkRecursionError` is
            raised on detection of cyclic symbolic links, if `True` (default), the
            cyclic link is represented by a `CyclicLinkedDir` object. See "Cyclic
            Links Handling" section below for further details.
        cache_file_apply: If set to `True`, the `file_apply` result will be cached
            by *real* path. Default `False`.
        include_empty (bool): If set to `True`, empty directories are included in
            the result of the recursive scanning, represented by an empty directory
            node: `DirNode(directories=[], files=[])`. If `False` (default), empty
            directories are not included in the parent directory node (and
            subsequently never passed to `dir_apply`).
        jobs (int | None): If `1` (default), no multiprocessing is used. If jobs > 1,
            the number of processes to use for parallelizing `file_apply` over
            included files. If `None`, `os.cpu_count()` number of processes are used.
            NOTE: if jobs is `None` or > 1, the entire file tree will first be stored
            in memory before applying `file_apply` and `dir_apply`.

    # Returns:
        The `object` returned by `dir_apply` on the `DirNode` for the top level
        `directory`. If the default value ("identity" function: `lambda x: x`) is
        used for `dir_apply`, it will be the `DirNode` representing the root node of
        the file tree.

    # Raises:
        SymlinkRecursionError: if `allow_cyclic_links=False` and any cyclic symbolic
            links are detected.

    # Cyclic Links Handling:
        Symbolically linked directories can create cycles in the, otherwise acyclic,
        graph representing the file tree. If not handled properly, this leads to
        infinite recursion when traversing the file tree (this is e.g. the case for
        Python's built-in `os.walk(directory, followlinks=True)`).

        Sometimes multiple links form cycles together, therefore - without loss of
        generality - cyclic links are defined as:

            The first occurrence of a link to a directory that has already been
            visited on the current branch of recursion.

        With `allow_cyclic_links=True` any link to such a directory is represented
        by the object `CyclicLinkedDir(path=..., target_path=...)` where `path` is
        the `RecursionPath` to the link and `target_path` the `RecursionPath` to the
        parent directory that is the target of the link.

        In the example below there are cycles on all branches A/B, A/C and D.

            root/
            |__A/
            |  |__B/
            |  |  |__toA@ -> ..
            |  |__C/
            |     |__toA@ -> ..
            |__D/
               |__toB@ -> ../A/B

        In this case, the symlinks with relative paths A/B/toA, A/C/toA and
        D/toB/toA/B/toA will be represented by a `CyclicLinkedDir` object. Note that
        for the third branch, the presence of cyclic links can be *detected* already
        at D/toB/toA/B (since B is already visited) but it is D/toB/toA/B/toA which
        is considered a cyclic link (and gets represented by a `CyclicLinkedDir`).
        This reflects the fact that it is the toA that's "causing" the cycle, not
        D/toB or D/toB/toA/B (which is not even a link), and at D/toB/toA/ the cycle
        can not yet be detected.

        Below is another example where multiple links are involved in forming cycles
        as well as links which absolute path is external to the root directory for
        the recursion. In this case the symlinks with relative paths A/toB/toA,
        B/toA/toB and C/toD/toC are considered cyclic links for
        `scandir('/path/to/root')`.

            /path/to/root/
                     |__A/
                     |  |__toB@ -> ../B
                     |__B/
                     |  |__toA@ -> /path/to/root/A
                     |__C/
                        |__toD@ -> /path/to/D

            /path/to/D/
                     |__toC@ -> /path/to/root/C
    """
    _verify_is_directory(directory)

    if jobs is None or jobs > 1:
        return _scantree_multiprocess(**vars())

    path = RecursionPath.from_root(directory)

    if cache_file_apply:
        file_apply = _cached_by_realpath(file_apply)

    root_dir_node = _scantree_recursive(
        path=path,
        recursion_filter=recursion_filter,
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
    """Multiprocess implementation of scantree.

    Note that it is only the `file_apply` function that is parallelized.
    """
    file_apply = kwargs.pop("file_apply")
    dir_apply = kwargs.pop("dir_apply")
    jobs = kwargs.pop("jobs")

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
    """Verify that `directory` path exists and is a directory, otherwise raise
    ValueError"""
    directory = fspath(directory)
    if not os.path.exists(directory):
        raise ValueError(f"{directory}: No such directory")
    if not os.path.isdir(directory):
        raise ValueError(f"{directory}: Is not a directory")


def _cached_by_realpath(file_apply):
    """Wrapps the `file_apply` function with a cache, if `path.real` is already in
    the cache, the cached value is returned"""
    cache = {}

    def file_apply_cached(path):
        if path.real not in cache:
            cache[path.real] = file_apply(path)
        return cache[path.real]

    return file_apply_cached


def _scantree_recursive(
    path,
    recursion_filter,
    file_apply,
    dir_apply,
    follow_links,
    allow_cyclic_links,
    include_empty,
    parents,
):
    """The underlying recursive implementation of scantree.

    # Arguments:
        path (RecursionPath): the recursion path relative the directory where
            recursion was initialized.
        recursion_filter (f: f([RecursionPath]) -> [RecursionPath]): A filter
            function, defining which files to include and which subdirectories to
            scan, e.g. an instance of `scantree.RecursionFilter`.
        file_apply (f: f(RecursionPath) -> object): The function to apply to the
            `RecursionPath` for each file. Default "identity", i.e. `lambda x: x`.
        dir_apply (f: f(DirNode) -> object): The function to apply to the `DirNode`
            for each (sub) directory. Default "identity", i.e. `lambda x: x`.
        follow_links (bool): Whether to follow symbolic links for not, i.e. to
            continue the recursive scanning in linked directories. If False, linked
            directories are represented by the `LinkedDir` object which does e.g.
            not have the `files` and `directories` properties (as these cannot be
            known without following the link). Default `True`.
        allow_cyclic_links (bool): If set to `False`, a `SymlinkRecursionError` is
            raised on detection of cyclic symbolic links, if `True` (default), the
            cyclic link is represented by a `CyclicLinkedDir` object.
        include_empty (bool): If set to `True`, empty directories are included in
            the result of the recursive scanning, represented by an empty directory
            node: `DirNode(directories=[], files=[])`. If `False` (default), empty
            directories are not included in the parent directory node (and
            subsequently never passed to `dir_apply`).
        parents ({str: RecursionPath}): Mapping from real path (`str`) to
            `RecursionPath` of parent directories.

    # Returns:
        `DirNode` for the directory at `path`.

    # Raises:
        SymlinkRecursionError: if `allow_cyclic_links=False` and any cyclic symbolic
            links are detected.
    """
    fwd_kwargs = vars()
    del fwd_kwargs["path"]

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
    for subpath in sorted(recursion_filter(path.scandir())):
        if subpath.is_dir():
            dir_node = _scantree_recursive(subpath, **fwd_kwargs)
            if include_empty or not is_empty_dir_node(dir_node):
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
        super().__init__(
            real_path=path.real,
            first_path=os.path.join(target_path.root, target_path.relative),
            second_path=os.path.join(path.root, path.relative),
        )

    def __str__(self):
        # _RecursionError.__str__ prints args without context
        return f"Symlink recursion: {self.message}"
