from __future__ import print_function, division

import pytest

from scantree.compat import fspath, scandir, DirEntry


class TestFSPath(object):

    def test_string(self):
        assert fspath('path/to') == 'path/to'

    def test__fspath__(self):

        class Path(object):

            def __init__(self, path):
                self.path = path

            def __fspath__(self):
                return self.path

        assert fspath(Path('path/to/this')) == 'path/to/this'

    def test_not_supported(self):
        with pytest.raises(TypeError):
            fspath(1)


class TestScandir(object):

    def test_basic(self, tmpdir):
        tmpdir.join('file').ensure()
        for path_like in [tmpdir, str(tmpdir)]:
            [de] = list(scandir(path_like))
            assert isinstance(de, DirEntry)
            assert de.name == 'file'

    def test_none_path(self, tmpdir):
        tmpdir.join('file').ensure()
        with tmpdir.as_cwd():
            [de] = list(scandir(None))
            assert isinstance(de, DirEntry)
            assert de.name == 'file'
