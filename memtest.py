"""
RAM test that runs inside Windows.

What it does: fills as much free memory as you allow with known patterns, reads everything back
and reports every byte that came back different. Several threads work in parallel, the byte
work happens in C (memset/memcpy/memcmp through ctypes, which releases Python's GIL), so this
really keeps the memory controller busy.

What it can't do (honest limits, shown in the app too):
- It only tests memory that Windows hands out. Whatever Windows and running programs occupy
  stays untested. For that, a test outside Windows is needed (Windows Memory Diagnostic or
  MemTest86), which Ramwise can schedule.
- It sees virtual addresses, not physical ones, so it can't tell which module is faulty.
- A pass doesn't prove the RAM is perfect. An error, on the other hand, is a real problem:
  faulty RAM or unstable overclock/XMP/EXPO settings.
"""

import ctypes
import ctypes.util
import os
import random
import threading
import time

MB = 1024 * 1024
GB = 1024 ** 3
CHUNK = 16 * MB          # unit of work
PAGE = 4096

# --- C helpers (GIL-free) ---------------------------------------------------
if os.name == "nt":
    _libc = ctypes.cdll.msvcrt
else:
    _libc = ctypes.CDLL(ctypes.util.find_library("c"))
_memset = _libc.memset
_memset.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
_memset.restype = ctypes.c_void_p
_memcpy = _libc.memcpy
_memcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
_memcpy.restype = ctypes.c_void_p
_memcmp = _libc.memcmp
_memcmp.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
_memcmp.restype = ctypes.c_int

PRESETS = {
    "quick":    {"name": "Quick", "share": 0.35, "passes": 1, "fade": False,
                 "desc": "About a third of your free RAM, one pass. A few minutes at most, finds clearly broken memory."},
    "standard": {"name": "Standard", "share": 0.60, "passes": 2, "fade": False,
                 "desc": "Most of your free RAM, two passes. Good after building a PC or changing RAM settings."},
    "thorough": {"name": "Thorough", "share": 0.75, "passes": 4, "fade": True,
                 "desc": "As much free RAM as is safe, four passes plus a bit fade test (patterns are left alone for a "
                         "minute and checked again). Use this when you suspect a problem."},
}

# name, kind, value
PATTERNS = [
    ("All zeros", "fill", 0x00), ("All ones", "fill", 0xFF),
    ("Checkerboard", "fill", 0x55), ("Inverse checkerboard", "fill", 0xAA),
    *[(f"Walking one, bit {b}", "fill", 1 << b) for b in range(8)],
    ("Random data", "random", None),
    ("Address stamps", "address", None),
]


def plan(available_bytes, preset):
    """How much to test and with how many threads, so Windows keeps enough breathing room."""
    p = PRESETS[preset]
    # never take the last 1.5 GB, and never more than the preset's share of what's free
    size = max(0, min(available_bytes * p["share"], available_bytes - 1.5 * GB))
    threads = max(1, min(8, (os.cpu_count() or 2) // 2))
    per = int(size // threads // CHUNK * CHUNK)
    while threads > 1 and per < 256 * MB:
        threads -= 1
        per = int(size // threads // CHUNK * CHUNK)
    return {"threads": threads, "per_thread": per, "total": per * threads, "passes": p["passes"],
            "fade": p["fade"]}


class _Region:
    """One thread's block of memory."""

    def __init__(self, size):
        self.buf = bytearray(size)      # zeroed, pages get committed as they're touched
        self.addr = ctypes.addressof((ctypes.c_char * size).from_buffer(self.buf))
        self.size = size


class MemTest:
    """Runs the test in background threads. Poll .status() from the UI."""

    def __init__(self, per_thread, threads, passes, fade=False):
        self.per_thread, self.threads, self.passes, self.fade = per_thread, threads, passes, fade
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()
        self.errors = []            # dicts, capped
        self.error_count = 0
        self.done_bytes = [0] * threads
        self.phase = "Preparing"
        self.pass_no = 1
        self.pattern_name = ""
        self.started = None
        self.finished = None
        self.failed = None          # message if the test couldn't run at all
        self.bytes_touched = 0
        # write + verify for every pattern in every pass, plus one bit fade round at the end
        self.work_per_thread = per_thread * (len(PATTERNS) * 2 * passes + (2 if fade else 0))
        self._threads = []

    # ---------------------------------------------------------------- run ---
    def start(self):
        self.started = time.time()
        self._runner = threading.Thread(target=self._run, daemon=True)
        self._runner.start()

    def stop(self):
        self.stop_flag.set()

    def _run(self):
        try:
            regions = []
            self.phase = "Reserving memory"
            for _ in range(self.threads):
                regions.append(_Region(self.per_thread))
        except MemoryError:
            self.failed = "Windows couldn't hand out that much memory. Close some programs or pick a smaller test."
            self.finished = time.time()
            return
        for i, reg in enumerate(regions):
            t = threading.Thread(target=self._worker, args=(i, reg), daemon=True)
            self._threads.append(t)
            t.start()
        for t in self._threads:
            t.join()
        del regions  # give the memory back right away
        self.phase = "Stopped" if self.stop_flag.is_set() else "Done"
        self.finished = time.time()

    def _worker(self, idx, reg):
        try:
            import psutil  # keep the rest of the PC usable while testing
            psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 5)
        except Exception:
            pass
        ref = bytearray(CHUNK)
        ref_addr = ctypes.addressof((ctypes.c_char * CHUNK).from_buffer(ref))
        rand_block = bytearray(4 * MB)
        rand_addr = ctypes.addressof((ctypes.c_char * len(rand_block)).from_buffer(rand_block))
        for pass_no in range(1, self.passes + 1):
            if idx == 0:
                self.pass_no = pass_no
            for name, kind, value in PATTERNS:
                if self.stop_flag.is_set():
                    return
                if idx == 0:
                    self.phase, self.pattern_name = "Testing", name
                seed = (pass_no * 7919 + idx * 104729) & 0xFFFFFFFF
                self._write(idx, reg, kind, value, ref, ref_addr, rand_block, rand_addr, seed)
                self._verify(idx, reg, kind, value, name, ref, ref_addr, rand_block, rand_addr, seed, pass_no)
            if self.fade and pass_no == self.passes and not self.stop_flag.is_set():
                if idx == 0:
                    self.phase, self.pattern_name = "Bit fade", "Pattern left alone for 60 s"
                self._write(idx, reg, "fill", 0xAA, ref, ref_addr, rand_block, rand_addr, 0)
                for _ in range(60):  # wait, but stay stoppable
                    if self.stop_flag.wait(1):
                        return
                self._verify(idx, reg, "fill", 0xAA, "Bit fade", ref, ref_addr, rand_block, rand_addr, 0, pass_no)

    # -------------------------------------------------------- patterns ---
    def _expected_chunk(self, kind, value, offset, n, ref, ref_addr, rand_block, rand_addr, seed):
        """Puts what chunk [offset, offset+n) should contain into ref. Returns its address."""
        if kind == "fill":
            return None  # handled with memset / cached ref
        if kind == "random":
            # a 4 MB random block, rotated differently for every chunk
            shift = (offset // CHUNK * 1_048_573 + seed) % len(rand_block)
            first = len(rand_block) - shift
            pos = 0
            while pos < n:
                take = min(first if pos == 0 else len(rand_block), n - pos)
                src = rand_addr + (shift if pos == 0 else 0)
                _memcpy(ref_addr + pos, src, take)
                pos += take
            return ref_addr
        return None

    def _write(self, idx, reg, kind, value, ref, ref_addr, rand_block, rand_addr, seed):
        if kind == "random":
            rand_block[:] = random.Random(seed).randbytes(len(rand_block))
        for off in range(0, reg.size, CHUNK):
            if self.stop_flag.is_set():
                return
            n = min(CHUNK, reg.size - off)
            if kind == "fill":
                _memset(reg.addr + off, value, n)
            elif kind == "random":
                self._expected_chunk(kind, value, off, n, ref, ref_addr, rand_block, rand_addr, seed)
                _memcpy(reg.addr + off, ref_addr, n)
            elif kind == "address":
                _memset(reg.addr + off, 0, n)
                buf = reg.buf
                for p in range(off, off + n, PAGE):  # every page gets its own number at both ends
                    stamp = (p // PAGE + idx * 0x100000000).to_bytes(8, "little")
                    buf[p:p + 8] = stamp
                    buf[p + PAGE - 8:p + PAGE] = stamp
            self._progress(idx, n)

    def _verify(self, idx, reg, kind, value, name, ref, ref_addr, rand_block, rand_addr, seed, pass_no):
        if kind == "fill":
            _memset(ref_addr, value, CHUNK)
        for off in range(0, reg.size, CHUNK):
            if self.stop_flag.is_set():
                return
            n = min(CHUNK, reg.size - off)
            if kind == "random":
                self._expected_chunk(kind, value, off, n, ref, ref_addr, rand_block, rand_addr, seed)
            elif kind == "address":
                _memset(ref_addr, 0, n)
                for p in range(0, n, PAGE):
                    stamp = ((off + p) // PAGE + idx * 0x100000000).to_bytes(8, "little")
                    ref[p:p + 8] = stamp
                    ref[p + PAGE - 8:p + PAGE] = stamp
            if _memcmp(reg.addr + off, ref_addr, n) != 0:
                self._record(idx, reg, off, n, ref, name, pass_no)
            self._progress(idx, n)

    def _record(self, idx, reg, off, n, ref, name, pass_no):
        """Finds the exact bad bytes in a chunk that didn't match."""
        bad_pages = 0
        first = None
        for p in range(0, n, PAGE):
            if _memcmp(reg.addr + off + p, ctypes.addressof((ctypes.c_char * PAGE).from_buffer(ref, p)), PAGE):
                bad_pages += 1
                if first is None:
                    got, want = reg.buf[off + p:off + p + PAGE], ref[p:p + PAGE]
                    for i in range(PAGE):
                        if got[i] != want[i]:
                            first = (off + p + i, want[i], got[i])
                            break
        with self.lock:
            self.error_count += max(1, bad_pages)
            if len(self.errors) < 200 and first:
                pos, want, got = first
                self.errors.append({"thread": idx, "offset": pos, "pattern": name, "pass": pass_no,
                                    "expected": want, "found": got, "flipped": want ^ got, "pages": bad_pages})

    def _progress(self, idx, n):
        self.done_bytes[idx] += n

    # ------------------------------------------------------------ status ---
    def status(self):
        total = self.work_per_thread * self.threads
        done = sum(self.done_bytes)
        elapsed = (self.finished or time.time()) - (self.started or time.time())
        rate = done / elapsed if elapsed > 0 else 0
        remaining = (total - done) / rate if rate > 0 and not self.finished else 0
        if self.fade and not self.finished:
            remaining += 60 if self.phase != "Bit fade" else 0
        return {
            "phase": self.phase, "pattern": self.pattern_name, "pass": self.pass_no, "passes": self.passes,
            "progress": min(1.0, done / total) if total else 0, "per_thread": [d / self.work_per_thread if
                                                                              self.work_per_thread else 0
                                                                              for d in self.done_bytes],
            "errors": self.error_count, "error_list": list(self.errors), "elapsed": elapsed,
            "remaining": remaining, "speed": rate, "finished": self.finished is not None,
            "failed": self.failed, "stopped": self.stop_flag.is_set(), "total_bytes": self.per_thread * self.threads,
        }
