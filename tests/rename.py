"""A displaced emulated hard link loses one name only when rename commits."""
import ctypes
import errno
import os
import tempfile
from pathlib import Path


renameat2 = ctypes.CDLL(None, use_errno=True).renameat2


def rename(src, dst, flags=0):
    if renameat2(-100, os.fsencode(src), -100, os.fsencode(dst), flags) == 0:
        return 0
    return ctypes.get_errno()


def check(root, case):
    src, dst, peer = (root / n for n in ("src", "dst", "peer"))
    dst.write_bytes(b"old")
    os.link(dst, peer)
    src.write_bytes(b"new")
    if case == "replace":
        os.replace(src, dst)
        assert not src.exists() and dst.read_bytes() == b"new"
        assert peer.read_bytes() == b"old" and peer.stat().st_nlink == 1
        return
    if case == "no-replace":
        assert rename(src, dst, 1) == errno.EEXIST
    elif case == "missing-source":
        assert rename(root / "missing", dst) == errno.ENOENT
    elif case == "exchange":
        source_peer = root / "source-peer"
        os.link(src, source_peer)
        assert rename(src, dst, 2) == 0
        assert os.path.samefile(src, peer) and os.path.samefile(dst, source_peer)
        assert dst.read_bytes() == b"new" and src.read_bytes() == b"old"
        assert src.stat().st_nlink == dst.stat().st_nlink == 2
        return
    elif case == "same-inode":
        os.rename(peer, dst)
    elif case == "same-name":
        os.rename(dst, dst)
    assert os.path.samefile(dst, peer)
    assert dst.read_bytes() == b"old" and dst.stat().st_nlink == 2
    assert src.read_bytes() == b"new"


for case in ("no-replace", "missing-source", "exchange", "same-inode", "same-name", "replace"):
    with tempfile.TemporaryDirectory() as directory:
        check(Path(directory), case)
        print("ok  ", case)
