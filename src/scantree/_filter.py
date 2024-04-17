from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from pathspec.util import match_file, normalize_file


class RecursionFilter:
    """Callable object for filtering of sequence of `RecursionPath`:s.

    Intended for use as `recursion_filter` argument in `scantree`.

    # Arguments:
        linked_dirs (bool): Whether to include linked directories. Default True.
        linked_files (bool): Whether to include linked files. Default True.
        match ([str] | None): List of gitignore-style wildcard match patterns. The
            `RecursionPath.relative` path must match at least one of the patterns
            not starting with `'!'` and none of the patterns starting with `'!'`.
            Matching is done based on the `pathspec` library implementation
            (https://github.com/cpburnz/python-path-specification). Default `None`
            which is equivalent to ['*'] matching all file paths.
    """

    def __init__(
        self,
        linked_dirs=True,
        linked_files=True,
        match=None,
    ):
        self.linked_dirs = linked_dirs
        self.linked_files = linked_files
        self._match_patterns = tuple("*") if match is None else tuple(match)
        if self._match_patterns != tuple("*"):
            self._path_spec = PathSpec.from_lines(
                GitWildMatchPattern, self.match_patterns
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
            # only filepaths are matched against patterns
            return True

        return self.match_file(recursion_path.relative)

    def match_file(self, filepath):
        """Match file against match patterns.

        NOTE: only match patterns are considered, not the `linked_files` argument of
        this class.

        # Arguments:
            filepath (str): the path to match.

        # Returns:
            Boolean, whether the path is a match or not.
        """
        if self._path_spec is None:
            return True
        return match_file(self._path_spec.patterns, normalize_file(filepath))

    def __call__(self, paths):
        """Filter recursion paths.

        # Arguments:
            paths ([RecursionPath]): The recursion paths to filter.

        # Returns:
            A generator of (filtered) recursion paths.
        """
        for path in paths:
            if self.include(path):
                yield path
