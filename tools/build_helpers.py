"""
Small helpers for build.bat and the GitHub workflow, so the version number lives in one place
(VERSION in core.py) and everything else is derived from it.

    python tools/build_helpers.py version               prints 1.1
    python tools/build_helpers.py version-info OUT      writes the exe version resource
    python tools/build_helpers.py msix-version          prints 1.1.0.0 (Store format)
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def version():
    with open(os.path.join(ROOT, "core.py"), encoding="utf-8") as f:
        return re.search(r'^VERSION = "([^"]+)"', f.read(), re.M).group(1)


def parts(v):
    nums = [int(x) for x in re.findall(r"\d+", v)][:3]
    return (nums + [0, 0, 0])[:3]


VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({a}, {b}, {c}, 0), prodvers=({a}, {b}, {c}, 0), mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Comroboter'),
      StringStruct('FileDescription', 'RAMCheck'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'RAMCheck'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 Comroboter, MIT License'),
      StringStruct('OriginalFilename', 'RAMCheck.exe'),
      StringStruct('ProductName', 'RAMCheck'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "version"
    v = version()
    if cmd == "version":
        print(v)
    elif cmd == "msix-version":
        print(".".join(str(x) for x in parts(v)) + ".0")
    elif cmd == "version-info":
        a, b, c = parts(v)
        os.makedirs(os.path.dirname(os.path.abspath(sys.argv[2])), exist_ok=True)
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(VERSION_INFO.format(a=a, b=b, c=c, v=v))
    else:
        sys.exit(f"unknown command {cmd}")
