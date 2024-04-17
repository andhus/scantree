import attr

from ._path import RecursionPath


@attr.s(slots=True, frozen=True)
class DirNode:
    """A directory node in a Directed Acyclic Graph (DAG) representing a file system
    tree.

    NOTE: this class is normally only ever instantiated by the `scantree` function.

    # Arguments:
        path (RecursionPath): The recursion path to the directory.
        directories ([object]): The result of `scantree` `dir_apply` argument
            applied to the subdirectories of this directory.
        files ([object]): The result of `scantree` `file_apply` argument
            applied to the files of this directory.
    """

    path = attr.ib(validator=attr.validators.instance_of(RecursionPath))
    files = attr.ib(default=(), converter=tuple)
    directories = attr.ib(default=(), converter=tuple)

    @property
    def empty(self):
        """Boolean: does this directory node have any files or subdirectories."""
        return not (self.files or self.directories)

    @property
    def entries(self):
        """Tuple of files followed by directories."""
        return self.files + self.directories

    def apply(self, dir_apply, file_apply):
        """Operate on the file tree under this directory node recursively.

        # Arguments:
            file_apply (f: f(object) -> object): The function to apply to the
                to each file. Default "identity", i.e. `lambda x: x`.
            dir_apply (f: f(DirNode) -> object): The function to apply to the
                `DirNode` for each (sub) directory. Default "identity", i.e.
                `lambda x: x`.

        # Returns:
            The `object` returned by `dir_apply` on this `DirNode` after recursive
            application of `file_apply` and `dir_apply` on its subdirectories and
            files.
        """
        dir_node = DirNode(
            self.path,
            [dir_.apply(dir_apply, file_apply) for dir_ in self.directories],
            [file_apply(file_) for file_ in self.files],
        )
        return dir_apply(dir_node)

    def leafpaths(self):
        """Get the leafs of the file tree under this directory node.

        # Returns:
            A list of `RecursionPaths` sorted on relative path. If the tree contains
            empty directories, `LinkedDir` or `CyclicLinkedDir` nodes these will be
            included. If none of these are present (which is the case for the result
            of `scantree('.', include_empty=False, follow_links=True,
            allow_cyclic_links=False)`) this method will only return paths to the
            files, i.e. the same as the `filepaths` method.

        NOTE: `LinkedDir` and `CyclicLinkedDir` nodes are considered leafs since
        they are leafs in the actual DAG data structure, even though they are not
        necessarily leafs in terms of the underlying file-system structure that they
        represent.
        """
        leafs = []

        def file_apply(path):
            leafs.append(path)

        def dir_apply(dir_node):
            if isinstance(dir_node, (LinkedDir, CyclicLinkedDir)) or dir_node.empty:
                leafs.append(dir_node.path)

        self.apply(dir_apply=dir_apply, file_apply=file_apply)

        return sorted(leafs, key=lambda path: path.relative)

    def filepaths(self):
        """Get the filepaths of the file tree under this directory.

        # Returns:
           A list of `RecursionPaths` sorted on relative path.
        """
        files = []

        def file_apply(path):
            files.append(path)

        self.apply(dir_apply=identity, file_apply=file_apply)

        return sorted(files, key=lambda path: path.relative)


@attr.s(slots=True, frozen=True)
class LinkedDir:
    """This node represents a symbolic link to a directory.

    It is created by `scantree` to represent a linked directory when the argument
    `follow_links` is set tot `False`.

    NOTE: this class is normally only ever instantiated by the `scantree` function.

    # Arguments:
        path (RecursionPath): The recursion path to the *link* to a directory.
    """

    path = attr.ib(validator=attr.validators.instance_of(RecursionPath))

    @property
    def directories(self):
        raise AttributeError(
            "`directories` is undefined for `LinkedDir` nodes. Use e.g. "
            "`[de for de in scandir(linked_dir.path.real) if de.is_dir()]` "
            "to get a list of the sub directories of the linked directory"
        )

    @property
    def files(self):
        raise AttributeError(
            "`files` is undefined for `LinkedDir` nodes. Use e.g. "
            "`[de for de in scandir(linked_dir.path.real) if de.is_file()]` "
            " to get a list of the files of the linked directory"
        )

    @property
    def entries(self):
        raise AttributeError(
            "`entries` is undefined for `LinkedDir` nodes. Use e.g. "
            "`scandir(linked_dir.path.real)` to get the entries of the linked "
            "directory"
        )

    @property
    def empty(self):
        raise AttributeError("`empty` is undefined for `LinkedDir` nodes.")

    def apply(self, dir_apply, file_apply=None):
        return dir_apply(self)


@attr.s(slots=True, frozen=True)
class CyclicLinkedDir:
    """This node represents a symbolic link causing a cycle of symlinks.

    It is created by `scantree` to represent a cyclic links when the argument
    `allow_cyclic_links` is set tot `True`.

    NOTE: this class is normally only ever instantiated by the `scantree` function.

    # Arguments:
        path (RecursionPath): The recursion path to the *symlink* to a directory
            (which is a parent of this directory).
        target_path (RecursionPath): The recursion path to the target directory of
            the link (which is a parent of this directory).
    """

    path = attr.ib(validator=attr.validators.instance_of(RecursionPath))
    target_path = attr.ib(validator=attr.validators.instance_of(RecursionPath))

    @property
    def directories(self):
        raise AttributeError(
            "`directories` is undefined for `CyclicLinkedDir` to avoid infinite "
            "recursion. `target_path` property contains the `RecursionPath` for the "
            "target directory."
        )

    @property
    def files(self):
        raise AttributeError(
            "`files` is undefined for `CyclicLinkedDir` to avoid infinite "
            "recursion. `target_path` property contains the `RecursionPath` for the "
            "target directory."
        )

    @property
    def entries(self):
        raise AttributeError(
            "`entries` is undefined for `CyclicLinkedDir` to avoid infinite "
            "recursion. `target_path` property contains the `RecursionPath` for the "
            "target directory."
        )

    @property
    def empty(self):
        """A cyclic linked dir is never empty."""
        return False

    def apply(self, dir_apply, file_apply=None):
        return dir_apply(self)


def is_empty_dir_node(dir_node):
    return isinstance(dir_node, DirNode) and dir_node.empty


def identity(x):
    return x
