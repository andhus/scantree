[![codecov](https://codecov.io/gh/andhus/scantree/branch/master/graph/badge.svg)](https://codecov.io/gh/andhus/scantree)

# `scantree`

Recursive directory iterator supporting:

- flexible filtering including wildcard path matching
- in memory representation of file-tree (for repeated access)
- efficient access to directory entry properties (`posix.DirEntry` interface) extended with real path and path relative to the recursion root directory
- detection and handling of cyclic symlinks

## Installation

```commandline
pip install scantree
```

## Usage

See source code for full documentation, some generic examples below.

Get matching file paths:

```python
from scantree import scantree, RecursionFilter

tree = scantree('/path/to/dir', RecursionFilter(match=['*.txt']))
print([path.relative for path in tree.filepaths()])
print([path.real for path in tree.filepaths()])
```

```
['d1/d2/file3.txt', 'd1/file2.txt', 'file1.txt']
['/path/to/other_dir/file3.txt', '/path/to/dir/d1/file2.txt', '/path/to/dir/file1.txt']
```

Access metadata of directory entries in file tree:

```python
d2 = tree.directories[0].directories[0]
print(type(d2))
print(d2.path.absolute)
print(d2.path.real)
print(d2.path.is_symlink())
print(d2.files[0].relative)
```

```
scantree._node.DirNode
/path/to/dir/d1/d2
/path/to/other_dir
True
d1/d2/file3.txt
```

Aggregate information by operating on tree:

```python
hello_count = tree.apply(
    file_apply=lambda path: sum([
        w.lower() == 'hello' for w in
        path.as_pathlib().read_text().split()
    ]),
    dir_apply=lambda dir_: sum(dir_.entries),
)
print(hello_count)
```

```
3
```

```python
hello_count_tree =  tree.apply(
    file_apply=lambda path: {
        'name': path.name,
        'count': sum([
            w.lower() == 'hello'
            for w in path.as_pathlib().read_text().split()
        ])
    },
    dir_apply=lambda dir_: {
        'name': dir_.path.name,
        'count': sum(e['count'] for e in dir_.entries),
        'sub_counts': [e for e in dir_.entries]
    },
)
from pprint import pprint
pprint(hello_count_tree)
```

```
{'count': 3,
 'name': 'dir',
 'sub_counts': [{'count': 2, 'name': 'file1.txt'},
                {'count': 1,
                 'name': 'd1',
                 'sub_counts': [{'count': 1, 'name': 'file2.txt'},
                                {'count': 0,
                                 'name': 'd2',
                                 'sub_counts': [{'count': 0,
                                                 'name': 'file3.txt'}]}]}]}
```

Flexible filtering:

```python
without_hidden_files = scantree('.', RecursionFilter(match=['*', '!.*']))

without_palindrome_linked_dirs = scantree(
    '.',
    lambda paths: [
        p for p in paths if not (
            p.is_dir() and
            p.is_symlink() and
            p.name == p.name[::-1]
        )
    ]
)
```

Comparison:

```python
tree = scandir('path/to/dir')
# make some operations on filesystem, make sure file tree is the same:
assert tree == scandir('path/to/dir')

# tree contains absolute/real path info:
import shutil
shutil.copytree('path/to/dir', 'path/to/other_dir')
new_tree = scandir('path/to/other_dir')
assert tree != new_tree
assert (
    [p.relative for p in tree.leafpaths()] ==
    [p.relative for p in new_tree.leafpaths()]
)
```

Inspect symlinks:

```python
from scantree import CyclicLinkedDir

file_links = []
dir_links = []
cyclic_links = []

def file_apply(path):
    if path.is_symlink():
        file_links.append(path)

def dir_apply(dir_node):
    if dir_node.path.is_symlink():
        dir_links.append(dir_node.path)
    if isinstance(dir_node, CyclicLinkedDir):
        cyclic_links.append((dir_node.path, dir_node.target_path))

scantree('.', file_apply=file_apply, dir_apply=dir_apply)
```
