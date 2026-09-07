#!/usr/bin/python3 -I
"""Read static assets as lab, never root; reject links and special objects."""
import base64
import json
import os
import stat
import sys

MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 10000

def export(root):
    total = 0
    entries = []
    def walk(fd, prefix=''):
        nonlocal total
        for filename in sorted(os.listdir(fd)):
            path = prefix + filename
            child = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                info = os.fstat(child)
                if stat.S_ISDIR(info.st_mode):
                    if path.count('/') > 32:
                        raise ValueError('static directory nesting exceeds 32')
                    walk(child, path + '/')
                elif stat.S_ISREG(info.st_mode):
                    if len(entries) >= MAX_FILES or info.st_size > MAX_TOTAL - total:
                        raise ValueError('static snapshot exceeds size/file limit')
                    data = bytearray()
                    while True:
                        block = os.read(child, min(65536, MAX_TOTAL - total + 1))
                        if not block:
                            break
                        total += len(block)
                        if total > MAX_TOTAL:
                            raise ValueError('static snapshot exceeds size limit')
                        data.extend(block)
                    entries.append({'path':path, 'data':base64.b64encode(data).decode('ascii')})
                else:
                    raise ValueError('static snapshot rejects special files')
            finally:
                os.close(child)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        walk(fd)
    finally:
        os.close(fd)
    return entries

if __name__ == '__main__':
    if os.geteuid() == 0:
        raise SystemExit('static exporter must run as deployment user')
    print(json.dumps(export(sys.argv[1])))
