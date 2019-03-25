from __future__ import print_function, division

import attr

from ._path import RecursionPath


@attr.s(slots=True, frozen=True)
class DirNode(object):
    path = attr.ib(validator=attr.validators.instance_of(RecursionPath))
    directories = attr.ib(default=tuple(), converter=tuple)
    files = attr.ib(default=tuple(), converter=tuple)

    @property
    def empty(self):
        return not (self.directories or self.files)

    @property
    def entries(self):
        return self.files + self.directories

    def apply(self, dir_apply, file_apply):
        dir_node = DirNode(
            self.path,
            [dir_.apply(dir_apply, file_apply) for dir_ in self.directories],
            [file_apply(file_) for file_ in self.files]
        )
        return dir_apply(dir_node)

    def leafpaths(self):
        leafs = []

        def file_apply(path):
            leafs.append(path)

        def dir_apply(dir_node):
            if isinstance(dir_node, (LinkedDir, CyclicLinkedDir)) or dir_node.empty:
                leafs.append(dir_node.path)

        self.apply(dir_apply=dir_apply, file_apply=file_apply)

        return sorted(leafs, key=lambda path: path.relative)

    def filepaths(self):
        files = []

        def file_apply(path):
            files.append(path)

        self.apply(dir_apply=identity, file_apply=file_apply)

        return sorted(files, key=lambda path: path.relative)


@attr.s(slots=True, frozen=True)
class LinkedDir(object):
    path = attr.ib(validator=attr.validators.instance_of(RecursionPath))

    @property
    def empty(self):
        raise NotImplementedError('`empty` is undefined for `LinkedDir` nodes.')

    def apply(self, dir_apply, file_apply=None):
        return dir_apply(self)


@attr.s(slots=True, frozen=True)
class CyclicLinkedDir(object):
    path = attr.ib(validator=attr.validators.instance_of(RecursionPath))
    target_path = attr.ib(validator=attr.validators.instance_of(RecursionPath))

    @property
    def empty(self):
        """A cyclic linked dir is never empty."""
        return False

    def apply(self, dir_apply, file_apply=None):
        return dir_apply(self)


def _is_empty_dir_node(dir_node):
    return isinstance(dir_node, DirNode) and dir_node.empty


def identity(x):
    return x
