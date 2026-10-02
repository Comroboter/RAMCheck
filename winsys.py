"""
Windows specific helpers: autostart entries, services, file publisher info, open windows.

Turning autostart off works exactly like the Task Manager: the entry stays where it is and
gets marked as disabled under ...\\Explorer\\StartupApproved. It shows up as "Disabled" in
Task Manager and can be turned back on there or in Ramwise. Services are set to "Manual"
(they still start when an app actually asks for them), the previous start type is logged
so it can be restored.

On other systems every function returns "nothing found", so the rest of the app still works.
"""

import json
import ntpath
import os
import re
import struct
import subprocess
import time

import psutil

IS_WIN = os.name == "nt"
if IS_WIN:
    import ctypes
    import winreg
    from ctypes import wintypes

WINDIR = (os.environ.get("WINDIR") or r"C:\Windows").lower().rstrip("\\") + "\\"
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW, keeps sc.exe from flashing a console
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
RUN_KEYS = [
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run", "Run", "Startup app (your user)"),
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Run", "Startup app (all users)"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "Run32", "Startup app (all users)"),
]


def _changes_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    return os.path.join(base, "Ramwise", "changes.json")


def load_changes():
    try:
        with open(_changes_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"services": {}}


def _save_changes(ch):
    os.makedirs(os.path.dirname(_changes_path()), exist_ok=True)
    with open(_changes_path(), "w", encoding="utf-8") as f:
        json.dump(ch, f, indent=2)


# ------------------------------------------------------- file details ---

_info_cache = {}


def file_info(path):
    """Publisher and description from the exe's version info, e.g. GIGABYTE / EasyTune Engine."""
    if not IS_WIN or not path:
        return {}
    if path in _info_cache:
        return _info_cache[path]
    out = {}
    try:
        ver = ctypes.windll.version
        ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        ver.GetFileVersionInfoSizeW.restype = wintypes.DWORD
        ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
        ver.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR,
                                       ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
        size = ver.GetFileVersionInfoSizeW(path, None)
        if size:
            buf = ctypes.create_string_buffer(size)
            pbuf = ctypes.cast(buf, ctypes.c_void_p)
            if ver.GetFileVersionInfoW(path, 0, size, pbuf):
                ptr, ln = ctypes.c_void_p(), wintypes.UINT()
                codes = []
                if ver.VerQueryValueW(pbuf, r"\VarFileInfo\Translation", ctypes.byref(ptr), ctypes.byref(ln)) and ln.value >= 4:
                    lang, cp = struct.unpack("<HH", ctypes.string_at(ptr.value, 4))
                    codes.append(f"{lang:04x}{cp:04x}")
                codes += ["040904b0", "040904e4", "000004b0"]
                for field, key in (("CompanyName", "company"), ("FileDescription", "description"),
                                   ("ProductName", "product")):
                    for code in codes:
                        if ver.VerQueryValueW(pbuf, f"\\StringFileInfo\\{code}\\{field}",
                                              ctypes.byref(ptr), ctypes.byref(ln)) and ln.value > 1:
                            value = ctypes.wstring_at(ptr.value, ln.value).split("\x00")[0].strip()
                            if value:
                                out[key] = value[:80]
                                break
    except Exception:
        pass
    _info_cache[path] = out
    return out


def visible_window_pids():
    """PIDs that own a real, visible top-level window (not tray-only background stuff)."""
    if not IS_WIN:
        return set()
    pids = set()
    try:
        user32, dwm = ctypes.windll.user32, ctypes.windll.dwmapi
        proc_t = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def cb(hwnd, _lparam):
            if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0 \
                    and not user32.GetWindow(hwnd, 4):  # 4 = GW_OWNER, only unowned windows
                cloaked = ctypes.c_int(0)
                dwm.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
                if not cloaked.value:  # hidden UWP windows are "visible" but cloaked
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    pids.add(pid.value)
            return True
        user32.EnumWindows(proc_t(cb), 0)
    except Exception:
        pass
    return pids


# ------------------------------------------------------------ services ---

_svc_cache = {"time": 0, "data": []}


START_TYPES = {2: "automatic", 3: "manual", 4: "disabled"}


def _reg_value(key, name):
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def list_services(max_age=60):
    """Windows services, read straight from the registry. Asking the service manager about each one
    (what psutil does) takes a second or more and made the window stutter right after start."""
    if not IS_WIN:
        return []
    if time.time() - _svc_cache["time"] < max_age:
        return _svc_cache["data"]
    out = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services") as root:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, name) as k:
                        kind = _reg_value(k, "Type")
                        if not isinstance(kind, int) or not kind & 0x30:  # 0x10/0x20: real services, no drivers
                            continue
                        display = str(_reg_value(k, "DisplayName") or name)
                        if display.startswith("@"):  # points into a resource file, not readable as is
                            display = name
                        out.append({"name": name, "display": display, "pid": None,
                                    "start": START_TYPES.get(_reg_value(k, "Start"), "other"),
                                    "binpath": os.path.expandvars(str(_reg_value(k, "ImagePath") or "")),
                                    "status": ""})
                except OSError:
                    continue
    except OSError:
        pass
    _svc_cache.update(time=time.time(), data=out)
    return out


def services_by_exe():
    """{lowercase exe path: [services]} so running programs can be recognized as services."""
    by = {}
    for s in list_services():
        exe = exe_from_command(s["binpath"]).lower()
        if exe and "svchost" not in exe:
            by.setdefault(exe, []).append(s)
    return by


def _is_windows_service(s):
    path = exe_from_command(s["binpath"]).lower()
    return path.startswith(WINDIR) or "svchost" in path or not path


def _is_delayed(name):
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SYSTEM\CurrentControlSet\Services\{name}") as k:
            return winreg.QueryValueEx(k, "DelayedAutostart")[0] == 1
    except OSError:
        return False


def _sc(*args):
    try:
        r = subprocess.run(["sc.exe", *args], capture_output=True, text=True, errors="replace",
                           creationflags=NO_WINDOW if IS_WIN else 0, timeout=20)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def _sc_message(code, name):
    if code == 5:
        return f"{name}: needs admin rights. Click Run as admin and try again."
    if code == 1060:
        return f"{name}: service not found."
    return f"{name}: Windows answered with error {code}."


def stop_service(name, label=None):
    code, _ = _sc("stop", name)
    if code in (0, 1062):  # 1062 = wasn't running anyway
        return True, ""
    return False, _sc_message(code, label or name)


# ------------------------------------------------------------- startup ---

def exe_from_command(cmd):
    """C:\\Path\\app.exe from '"C:\\Path\\app.exe" --minimized' and similar."""
    cmd = os.path.expandvars((cmd or "").strip())
    if not cmd:
        return ""
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        return cmd[1:end] if end > 0 else cmd[1:]
    m = re.match(r"(.+?\.exe)\b", cmd, re.IGNORECASE)
    return m.group(1) if m else cmd.split(" ")[0]


def _lnk_target(path):
    """Target of a .lnk shortcut, read straight from the file format (no COM needed)."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        if data[:4] != b"\x4c\x00\x00\x00":
            return ""
        flags = struct.unpack_from("<I", data, 0x14)[0]
        pos = 0x4C
        if flags & 0x01:  # HasLinkTargetIDList
            pos += 2 + struct.unpack_from("<H", data, pos)[0]
        if flags & 0x02:  # HasLinkInfo
            _size, header, li_flags = struct.unpack_from("<III", data, pos)
            if li_flags & 0x01:
                if header >= 0x24:
                    off_u = struct.unpack_from("<I", data, pos + 0x1C)[0]
                    if off_u:
                        raw, i = b"", pos + off_u
                        while data[i:i + 2] != b"\x00\x00":
                            raw += data[i:i + 2]
                            i += 2
                        return raw.decode("utf-16-le", errors="replace")
                off = struct.unpack_from("<I", data, pos + 0x10)[0]
                end = data.index(b"\x00", pos + off)
                return data[pos + off:end].decode("mbcs" if IS_WIN else "latin-1", errors="replace")
    except Exception:
        pass
    return ""


def _root(hive):
    return winreg.HKEY_CURRENT_USER if hive == "HKCU" else winreg.HKEY_LOCAL_MACHINE


def _approved_enabled(hive, sub, name):
    try:
        with winreg.OpenKey(_root(hive), f"{APPROVED}\\{sub}", 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            data, _ = winreg.QueryValueEx(k, name)
            return not (data and data[0] & 1)  # 02/06 = on, 03/07 = off
    except OSError:
        return True  # no record means on


def startup_entries():
    """Everything that starts with Windows that Ramwise can turn off and on again."""
    if not IS_WIN:
        return []
    out = []
    for hive, path, sub, label in RUN_KEYS:
        try:
            with winreg.OpenKey(_root(hive), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                i = 0
                while True:
                    try:
                        name, cmd, _ = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    out.append({"id": f"run|{hive}|{sub}|{name}", "kind": "run", "name": name,
                                "label": label, "command": str(cmd), "exe": exe_from_command(str(cmd)),
                                "hive": hive, "sub": sub, "enabled": _approved_enabled(hive, sub, name),
                                "needs_admin": hive == "HKLM"})
        except OSError:
            continue
    folders = [
        ("HKCU", os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"),
         "Startup folder (your user)"),
        ("HKLM", os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs\StartUp"),
         "Startup folder (all users)"),
    ]
    for hive, folder, label in folders:
        try:
            files = os.listdir(folder)
        except OSError:
            continue
        for fn in files:
            if fn.lower() == "desktop.ini":
                continue
            full = os.path.join(folder, fn)
            target = _lnk_target(full) if fn.lower().endswith(".lnk") else full
            out.append({"id": f"folder|{hive}|{fn}", "kind": "folder", "name": os.path.splitext(fn)[0],
                        "file": fn, "label": label, "command": target or full, "exe": target,
                        "hive": hive, "sub": "StartupFolder",
                        "enabled": _approved_enabled(hive, "StartupFolder", fn), "needs_admin": hive == "HKLM"})
    changed = load_changes()["services"]
    for s in list_services():
        if _is_windows_service(s):
            continue
        if s["start"] == "automatic" or s["name"] in changed:
            out.append({"id": f"service|{s['name']}", "kind": "service", "name": s["display"] or s["name"],
                        "service": s["name"], "label": "Service", "command": s["binpath"],
                        "exe": exe_from_command(s["binpath"]), "pid": s["pid"],
                        "enabled": s["start"] == "automatic", "needs_admin": True})
    return out


def set_startup_enabled(entry, enabled):
    """Returns (ok, message)."""
    if not IS_WIN:
        return False, "Only works on Windows."
    if entry["kind"] == "service":
        name = entry["service"]
        changes = load_changes()
        previous = "delayed-auto" if _is_delayed(name) else "auto"
        if enabled:
            code, _ = _sc("config", name, "start=", changes["services"].get(name, "auto"))
        else:
            code, _ = _sc("config", name, "start=", "demand")
        if code != 0:
            return False, _sc_message(code, entry["name"])
        if enabled:
            changes["services"].pop(name, None)
        else:
            changes["services"].setdefault(name, previous)
        _save_changes(changes)
        return True, ""
    value_name = entry["file"] if entry["kind"] == "folder" else entry["name"]
    if enabled:
        data = bytes([2]) + bytes(11)
    else:
        filetime = int((time.time() + 11644473600) * 10_000_000)
        data = bytes([3, 0, 0, 0]) + struct.pack("<Q", filetime)
    try:
        with winreg.CreateKeyEx(_root(entry["hive"]), f"{APPROVED}\\{entry['sub']}", 0,
                                winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.SetValueEx(k, value_name, 0, winreg.REG_BINARY, data)
        return True, ""
    except PermissionError:
        return False, f"{entry['name']}: needs admin rights. Click Run as admin and try again."
    except OSError as e:
        return False, f"{entry['name']}: {e}"


def match_entries(entries, groups):
    """Which autostart entries belong to which running program. Returns {group key: [entries]}."""
    by_key = {}
    for g in groups:
        exe = (g.get("exe") or "").lower()
        pids = set(g.get("pids") or [])
        for e in entries:
            e_exe = (e.get("exe") or "").lower()
            hit = (e_exe and exe and e_exe == exe) \
                or (e_exe and ntpath.basename(e_exe) == g["key"]) \
                or (e["kind"] == "service" and e.get("pid") in pids) \
                or (e["kind"] != "service" and g["key"].endswith(".exe")
                    and g["key"] in (e.get("command") or "").lower())  # e.g. Update.exe --processStart Discord.exe
            if hit:
                by_key.setdefault(g["key"], []).append(e)
    return by_key
