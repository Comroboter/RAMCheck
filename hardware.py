"""
Facts about the installed RAM and Windows' own memory test.

- Modules: slot, size, type, speed, maker and part number (from WMI, read through PowerShell,
  so no extra Python packages are needed).
- Hints: RAM running below its rated speed (XMP/EXPO off), single channel, empty slots.
- Memory details: committed memory, page file, kernel memory, hardware reserved.
- Windows Memory Diagnostic: schedule it and read the result of the last run from the event log.

Everything returns empty results on other systems or when Windows says no.
"""

import ctypes
import json
import os
import re
import subprocess

GB = 1024 ** 3
NO_WINDOW = 0x08000000
MEMORY_TYPES = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 30: "LPDDR4", 34: "DDR5", 35: "LPDDR5"}


def _powershell_json(command, timeout=20):
    if os.name != "nt":
        return None
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            command + " | ConvertTo-Json -Depth 3"],
                           capture_output=True, text=True, errors="replace", timeout=timeout,
                           creationflags=NO_WINDOW)
        if r.returncode != 0 or not r.stdout.strip():
            return None
        data = json.loads(r.stdout)
        return data if isinstance(data, list) else [data]
    except Exception:
        return None


def rated_speed(part_number):
    """Speed a kit is sold as, read from its part number (e.g. CMK32GX5M2B6000C36 -> 6000). Best effort."""
    for m in re.finditer(r"(?<!\d)(\d{4})(?!\d)", part_number or ""):
        v = int(m.group(1))
        if 1600 <= v <= 10000 and v % 100 in (0, 33, 66, 67):
            return v
    m = re.search(r"(?:C|KF)(\d{3})C\d{2}", part_number or "", re.I)  # Kingston style: KF560C36 -> 5600
    if m:
        return int(m.group(1)) * 10
    return None


def modules():
    """List of installed modules, [] if unknown."""
    rows = _powershell_json("Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel, DeviceLocator, "
                            "Capacity, Speed, ConfiguredClockSpeed, Manufacturer, PartNumber, SMBIOSMemoryType")
    out = []
    for r in rows or []:
        part = (r.get("PartNumber") or "").strip()
        out.append({
            "slot": (r.get("DeviceLocator") or r.get("BankLabel") or "?").strip(),
            "bank": (r.get("BankLabel") or "").strip(),
            "size": int(r.get("Capacity") or 0),
            "type": MEMORY_TYPES.get(r.get("SMBIOSMemoryType") or 0, ""),
            "speed": int(r.get("ConfiguredClockSpeed") or 0),
            "max_speed": int(r.get("Speed") or 0),
            "maker": (r.get("Manufacturer") or "").strip(),
            "part": part,
            "rated": rated_speed(part),
        })
    return out


def slot_count():
    rows = _powershell_json("Get-CimInstance Win32_PhysicalMemoryArray | Select-Object MemoryDevices")
    try:
        return sum(int(r.get("MemoryDevices") or 0) for r in rows or []) or None
    except (TypeError, ValueError):
        return None


def hints(mods, slots=None):
    """Plain-language findings about the RAM setup. Each is (level, text), level 'warn' or 'info'."""
    out = []
    if not mods:
        return out
    speeds = {m["speed"] for m in mods if m["speed"]}
    rated = [m["rated"] for m in mods if m["rated"]]
    if speeds and rated:
        run, sold = min(speeds), min(rated)
        if abs(run * 2 - sold) <= 100:  # some boards report the clock (MHz), not the data rate (MT/s)
            run *= 2
        if run < sold - 100:
            out.append(("warn", f"Your RAM runs at {run} MT/s but is sold as {sold} MT/s. The XMP or EXPO profile is "
                                "probably switched off in the BIOS. Turning it on is usually a free speed boost."))
        else:
            out.append(("info", f"Running at its rated speed of {sold} MT/s."))
    if len(mods) == 1:
        out.append(("warn", "Only one module is installed, so the RAM runs in single channel mode. A second, "
                            "identical module would roughly double the memory bandwidth."))
    elif len({(m["size"], m["part"]) for m in mods}) > 1:
        out.append(("warn", "The modules aren't identical (size or part number differ). That often works, "
                            "but mixed kits are a common cause of instability, especially with XMP or EXPO."))
    if slots and len(mods) < slots:
        out.append(("info", f"{len(mods)} of {slots} slots are used."))
    return out


def performance_info():
    """Committed memory, cache and kernel memory in bytes (Windows GetPerformanceInfo)."""
    if os.name != "nt":
        return {}

    class PerfInfo(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_uint32)] + [(n, ctypes.c_size_t) for n in (
            "CommitTotal", "CommitLimit", "CommitPeak", "PhysicalTotal", "PhysicalAvailable", "SystemCache",
            "KernelTotal", "KernelPaged", "KernelNonpaged", "PageSize")] + [
            (n, ctypes.c_uint32) for n in ("HandleCount", "ProcessCount", "ThreadCount")]
    try:
        info = PerfInfo()
        info.cb = ctypes.sizeof(PerfInfo)
        if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(info), info.cb):
            return {}
        page = info.PageSize
        return {"commit": info.CommitTotal * page, "commit_limit": info.CommitLimit * page,
                "cache": info.SystemCache * page, "kernel_paged": info.KernelPaged * page,
                "kernel_nonpaged": info.KernelNonpaged * page, "processes": info.ProcessCount,
                "threads": info.ThreadCount, "handles": info.HandleCount}
    except Exception:
        return {}


def schedule_windows_test():
    """Opens Windows Memory Diagnostic (it asks whether to restart now or next time). Needs admin, so UAC asks."""
    if os.name != "nt":
        return False
    try:
        return ctypes.windll.shell32.ShellExecuteW(None, "runas", "mdsched.exe", None, None, 1) > 32
    except Exception:
        return False


def last_windows_test():
    """Result of the last Windows Memory Diagnostic run: {'date', 'ok'} or None.
    Reads the event as XML, so it works the same on every Windows language."""
    if os.name != "nt":
        return None
    try:
        r = subprocess.run(["wevtutil", "qe", "System", "/c:1", "/rd:true", "/f:xml",
                            "/q:*[System[Provider[@Name='Microsoft-Windows-MemoryDiagnostics-Results']]]"],
                           capture_output=True, text=True, errors="replace", timeout=15, creationflags=NO_WINDOW)
    except Exception:
        return None
    xml = r.stdout or ""
    event_id = re.search(r"<EventID[^>]*>(\d+)</EventID>", xml)
    when = re.search(r"SystemTime=['\"](\d{4}-\d{2}-\d{2})", xml)
    if not event_id:
        return None
    return {"date": when.group(1) if when else "", "ok": event_id.group(1) == "1201"}  # 1202 = errors found
