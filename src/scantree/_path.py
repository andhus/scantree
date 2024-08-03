from os import DirEntry, lstat, scandir, stat
from os import name as os_name
from os import path as os_path
from pathlib import Path

import attr

from .compat import fspath


@attr.s(slots=True)  # TODO consider make frozen.
class RecursionPath:
    """Caches the properties of directory entries including the path relative to the
    root directory for recursion.

    NOTE: this class is normally only ever instantiated by the `scantree` function.

    The class provides the os-portable `DirEntry` interface.
    """

    root = attr.ib()
    relative = attr.ib()
    real = attr.ib()
    _dir_entry = attr.ib(eq=False, order=False)

    @classmethod
    def from_root(cls, directory):
        """Instantiate a `RecursionPath` from given directory."""
        if isinstance(directory, (DirEntry, DirEntryReplacement)):
            dir_entry = directory
        else:
            dir_entry = DirEntryReplacement.from_path(directory)
        return cls(
            root=dir_entry.path,
            relative="",
            real=os_path.realpath(dir_entry.path),
            dir_entry=dir_entry,
        )

    def scandir(self):
        """Scan the underlying directory.

        # Returns:
            A generator of `RecursionPath`:s representing the directory entries.
        """
        return (self._join(dir_entry) for dir_entry in scandir(self.absolute))

    def _join(self, dir_entry):
        relative = os_path.join(self.relative, dir_entry.name)
        real = os_path.join(self.real, dir_entry.name)
        if dir_entry.is_symlink():
            # For large number of files/directories it improves performance
            # significantly to only call `os_path.realpath` when we are actually
            # encountering a symlink.
            real = os_path.realpath(real)

        return attr.evolve(self, relative=relative, real=real, dir_entry=dir_entry)

    @property
    def absolute(self):
        """The absolute path to this entry"""
        if self.relative == "":
            return self.root  # don't join in this case as that appends trailing '/'
        return os_path.join(self.root, self.relative)

    @property
    def path(self):
        """The path property according `DirEntry` interface.

        NOTE: this property is only here to fully implement the `DirEntry` interface
        (which is useful in comparison etc.). It is recommended to use one on of
        (the well defined) `real`, `relative` or `absolute` properties instead.
        """
        return self._dir_entry.path

    @property
    def name(self):
        return self._dir_entry.name

    def is_dir(self, follow_symlinks=True):
        return self._dir_entry.is_dir(follow_symlinks=follow_symlinks)

    def is_file(self, follow_symlinks=True):
        return self._dir_entry.is_file(follow_symlinks=follow_symlinks)

    def is_symlink(self):
        return self._dir_entry.is_symlink()

    def stat(self, follow_symlinks=True):
        return self._dir_entry.stat(follow_symlinks=follow_symlinks)

    def inode(self):
        return self._dir_entry.inode()

    def __fspath__(self):
        return self.absolute

    def as_pathlib(self):
        """Get a pathlib version of this path."""
        return Path(self.absolute)

    @staticmethod
    def _getstate(self):
        return (
            self.root,
            self.relative,
            self.real,
            DirEntryReplacement.from_dir_entry(self._dir_entry),
        )

    @staticmethod
    def _setstate(self, state):
        self.root, self.relative, self.real, self._dir_entry = state


# Attrs overrides __get/setstate__ for slotted classes, see:
# https://github.com/python-attrs/attrs/issues/512
RecursionPath.__getstate__ = RecursionPath._getstate
RecursionPath.__setstate__ = RecursionPath._setstate


@attr.s(slots=True, eq=False, order=False)
class DirEntryReplacement:
    """Pure python implementation of the os-portable `DirEntry` interface.


    A `DirEntry` cannot be instantiated directly (only returned from a call to
    `scandir`). This class offers a drop in replacement. Useful in testing and for
    representing the root directory for `scantree` implementation.
    """

    path = attr.ib(converter=fspath)
    name = attr.ib()
    _is_dir = attr.ib(init=False, default=None)
    _is_file = attr.ib(init=False, default=None)
    _is_symlink = attr.ib(init=False, default=None)
    _stat_sym = attr.ib(init=False, default=None)
    _stat_nosym = attr.ib(init=False, default=None)

    @classmethod
    def from_path(cls, path):
        path = fspath(path)
        if not os_path.exists(path):
            raise OSError(f"{path} does not exist")
        basename = os_path.basename(path)
        if basename in ["", ".", ".."]:
            name = os_path.basename(os_path.realpath(path))
        else:
            name = basename
        return cls(path, name)

    @classmethod
    def from_dir_entry(cls, dir_entry):
        return cls(dir_entry.path, dir_entry.name)

    def is_dir(self, follow_symlinks=True):
        if self._is_dir is None:
            self._is_dir = os_path.isdir(self.path)
        if follow_symlinks:
            return self._is_dir
        else:
            return self._is_dir and not self.is_symlink()

    def is_file(self, follow_symlinks=True):
        if self._is_file is None:
            self._is_file = os_path.isfile(self.path)
        if follow_symlinks:
            return self._is_file
        else:
            return self._is_file and not self.is_symlink()

    def is_symlink(self):
        if self._is_symlink is None:
            self._is_symlink = os_path.islink(self.path)
        return self._is_symlink

    def stat(self, follow_symlinks=True):
        if follow_symlinks:
            if self._stat_sym is None:
                self._stat_sym = stat(self.path)
            return self._stat_sym

        if self._stat_nosym is None:
            self._stat_nosym = lstat(self.path)
        return self._stat_nosym

    def inode(self):
        return self.stat(follow_symlinks=False).st_ino

    def __eq__(self, other):
        if not isinstance(other, (DirEntryReplacement, DirEntry)):
            return False
        if not self.path == other.path:
            return False
        if not self.name == other.name:
            return False
        methods = [
            ("is_dir", {"follow_symlinks": True}),
            ("is_dir", {"follow_symlinks": False}),
            ("is_file", {"follow_symlinks": True}),
            ("is_file", {"follow_symlinks": False}),
            ("is_symlink", {}),
        ]
        if os_name != "nt":  # pragma: no cover
            methods.extend(
                [
                    ("stat", {"follow_symlinks": True}),
                    ("stat", {"follow_symlinks": False}),
                    ("inode", {}),
                ]
            )

        for method, kwargs in methods:
            this_res = getattr(self, method)(**kwargs)
            other_res = getattr(other, method)(**kwargs)
            if not this_res == other_res:
                return False

        return True
