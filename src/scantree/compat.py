from __future__ import print_function, division

import sys
from six import string_types
import platform

def fspath(path):
    """In python 2: os.path... and scandir does not support PathLike objects"""
    if isinstance(path, string_types):
        return path
    if hasattr(path, '__fspath__'):
        return path.__fspath__()
    raise TypeError('Object {} is not a path'.format(path))


# Use the built-in version of scandir if possible (python > 3.5),
# otherwise use the scandir module version
try:
    from os import scandir
    if platform.system() != 'Windows':
        from posix import DirEntry
    else:
        from os import DirEntry
except ImportError:
    from scandir import scandir as _scandir
    from scandir import DirEntry

    def scandir(path, *args, **kwargs):
        if path is not None:
            path = fspath(path)
        return _scandir(path, *args, **kwargs)

if sys.version_info >= (3, 4):
    from pathlib import Path
else:
    from pathlib2 import Path
