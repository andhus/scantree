from __future__ import print_function, division

from pathspec import PathSpec
from pathspec.util import normalize_file, match_file
from pathspec.patterns import GitWildMatchPattern


class RecursionFilter(object):

    def __init__(
        self,
        linked_dirs=True,
        linked_files=True,
        match=None,
    ):
        self.linked_dirs = linked_dirs
        self.linked_files = linked_files
        self._match_patterns = tuple('*') if match is None else tuple(match)
        if self._match_patterns != tuple('*'):
            self._path_spec = PathSpec.from_lines(
                GitWildMatchPattern,
                self.match_patterns
            )
        else:
            self._path_spec = None

    @property
    def match_patterns(self):
        return self._match_patterns

    def include(self, recursion_path):
        if recursion_path.is_symlink():
            if recursion_path.is_dir() and not self.linked_dirs:
                return False
            if recursion_path.is_file() and not self.linked_files:
                return False

        if recursion_path.is_dir():
            # only filepaths matched against patterns
            return True

        return self.match_file(recursion_path.relative)

    def match_file(self, filepath):
        if self._path_spec is None:
            return True
        return match_file(self._path_spec.patterns, normalize_file(filepath))

    def __call__(self, paths):
        for path in paths:
            if self.include(path):
                yield path
