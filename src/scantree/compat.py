def fspath(path):
    """In python 2: os.path... and scandir does not support PathLike objects"""
    if isinstance(path, str):
        return path
    if hasattr(path, "__fspath__"):
        return path.__fspath__()
    raise TypeError(f"Object {path} is not a path")
