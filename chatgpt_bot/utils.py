from contextlib import contextmanager
import tempfile
import os
import shutil


@contextmanager
def temp_file(extention):
    dir = tempfile.mkdtemp()
    yield os.path.join(dir, f"temp{extention}")
    shutil.rmtree(dir)
