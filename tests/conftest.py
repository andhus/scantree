import functools
import os

import pytest


@functools.wraps(os.symlink)
def symlink(*args, **kwargs):
    try:
        return os.symlink(*args, **kwargs)
    except OSError as e:
        if os.name == "nt":
            pytest.xfail("Windows may lack symlink privilege.")
        else:
            raise e
