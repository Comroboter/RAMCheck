"""
Ramwise core: measuring, config, setup file and AI calls.
Shared by the window app (gui.py) and the terminal version (cli.py).
"""

import base64
import datetime as dt
import getpass
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict

import psutil

import winsys

VERSION = "1.4"
TAGLINE = "RAM analyzer & memory test"
TAGLINE_TITLE = "RAM Analyzer & Memory Test"
MB = 1024 * 1024
GB = 1024 ** 3
API_URL = "https://api.anthropic.com/v1/messages"
REPO_URL = "https://github.com/Comroboter/Ramwise"

# Where the AI runs. "cloud" needs an API key, "local" runs on this PC.
# Model names go stale quickly, so every provider can load its current list ("Load models").
PROVIDERS = {
    "claude": {"name": "Claude (Anthropic)", "where": "cloud", "api": "anthropic",
               "url": "https://api.anthropic.com/v1", "env": "ANTHROPIC_API_KEY",
               "models": ["claude-haiku-4-5-20251001", "claude-sonnet-5-5"],
               "key_url": "https://console.anthropic.com/settings/keys",
               "hint": "Haiku is cheap and usually good enough, roughly 1 to 3 cents per run. "
                       "Sonnet judges more carefully and costs a few times more."},
    "openai": {"name": "OpenAI", "where": "cloud", "api": "openai", "url": "https://api.openai.com/v1",
               "env": "OPENAI_API_KEY", "models": ["gpt-5.6-luna", "gpt-5.6-terra"],
               "key_url": "https://platform.openai.com/api-keys",
               "hint": "Luna is the cheap one and fine for this. Reasoning models take a bit longer."},
    "gemini": {"name": "Google Gemini", "where": "cloud", "api": "openai",
               "url": "https://generativelanguage.googleapis.com/v1beta/openai", "env": "GEMINI_API_KEY",
               "models": ["gemini-3.5-flash-lite", "gemini-3.6-flash"],
               "key_url": "https://aistudio.google.com/apikey",
               "hint": "Flash-Lite is fast and cheap. Google AI Studio has a free tier with rate limits."},
    "openrouter": {"name": "OpenRouter", "where": "cloud", "api": "openai", "url": "https://openrouter.ai/api/v1",
                   "env": "OPENROUTER_API_KEY", "models": ["openai/gpt-5.6-luna"],
                   "key_url": "https://openrouter.ai/settings/keys",
                   "hint": "One key for models from many companies. Click Load models to pick one."},
    "mistral": {"name": "Mistral", "where": "cloud", "api": "openai", "url": "https://api.mistral.ai/v1",
                "env": "MISTRAL_API_KEY", "models": ["mistral-small-latest", "mistral-medium-latest"],
                "key_url": "https://console.mistral.ai/api-keys",
                "hint": "European provider. Small is cheap and good enough for this."},
    "custom": {"name": "Other (OpenAI-compatible)", "where": "cloud", "api": "openai", "url": "",
               "env": "", "models": [], "key_url": "",
               "hint": "Any service with an OpenAI-compatible API, for example Groq, DeepSeek or a "
                       "server in your network. Enter its address (ending in /v1) and a model name."},
    "ollama": {"name": "Ollama", "where": "local", "api": "ollama", "url": "http://localhost:11434",
               "env": "", "models": ["qwen2.5:7b"], "key_url": "https://ollama.com/download",
               "hint": "Free, and nothing leaves your PC. Needs Ollama installed and a model downloaded."},
    "lmstudio": {"name": "LM Studio", "where": "local", "api": "openai", "url": "http://localhost:1234/v1",
                 "env": "", "models": [], "key_url": "https://lmstudio.ai",
                 "hint": "Free, and nothing leaves your PC. Load a model in LM Studio and start its "
                         "local server (Developer tab)."},
}
# Models worth downloading for Ollama: (name, download size, RAM while running)
OLLAMA_SUGGESTIONS = [("qwen2.5:7b", "4.7 GB", "about 6 GB"), ("qwen2.5:14b", "9.0 GB", "about 11 GB, best with 12+ GB VRAM"),
                      ("llama3.1:8b", "4.9 GB", "about 6 GB"),
                      ("qwen2.5:3b", "1.9 GB", "about 3 GB")]

DEFAULTS = {
    "provider": "claude",
    "models": {},
    "urls": {},
    "api_keys": {},
    "top": 40,
    "refresh_s": 10,
    "min_mb": 10,
    "double_check": True,
    "check_updates": True,
    "keep": [],
}

# Order = order in lists and in the memory map
CATEGORIES = {
    "bloatware": "Bloatware",
    "optional":  "Optional",
    "unknown":   "Unclear",
    "in_use":    "In use",
    "important": "Important",
    "system":    "Windows system",
}
CATEGORY_HINT = {
    "bloatware": "Junk you can get rid of",
    "optional":  "Only needed now and then",
    "unknown":   "Look this one up yourself",
    "in_use":    "Something you are using right now",
    "important": "Drivers, security or part of your setup",
    "system":    "Part of Windows, leave it alone",
}

# Never offer "End process" for these, no matter what the AI says
CRITICAL = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "lsaiso.exe", "winlogon.exe", "svchost.exe", "dwm.exe", "memcompression",
    "fontdrvhost.exe", "secure system", "explorer.exe", "sihost.exe", "ctfmon.exe",
    "conhost.exe", "runtimebroker.exe", "msmpeng.exe", "system idle process",
}


# Processes of the local AI engines. When one of them does the analysis, it must never be flagged.
ENGINE_PROCESSES = {
    "ollama": {"ollama.exe", "ollama app.exe", "ollama_llama_server.exe"},
    "lmstudio": {"lm studio.exe", "lms.exe", "llmworker.exe"},
}

# Real Windows components and where they live. Same name elsewhere = suspicious.
_DEFENDER = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), "Microsoft", "Windows Defender").lower()
SYSTEM_HOMES = {n: [winsys.WINDIR] for n in (
    "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "lsaiso.exe", "winlogon.exe", "svchost.exe",
    "dwm.exe", "smss.exe", "fontdrvhost.exe", "sihost.exe", "taskhostw.exe", "ctfmon.exe", "conhost.exe",
    "runtimebroker.exe", "searchindexer.exe", "searchhost.exe", "searchfilterhost.exe",
    "searchprotocolhost.exe", "spoolsv.exe", "wmiprvse.exe", "dllhost.exe", "audiodg.exe", "explorer.exe",
    "startmenuexperiencehost.exe", "shellexperiencehost.exe", "textinputhost.exe", "lockapp.exe",
    "securityhealthservice.exe", "securityhealthsystray.exe", "wudfhost.exe",
    "applicationframehost.exe", "systemsettings.exe", "useroobebroker.exe", "smartscreen.exe")}
_OLD_DEFENDER = os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Windows Defender").lower()
SYSTEM_HOMES["msmpeng.exe"] = [_DEFENDER, _OLD_DEFENDER, winsys.WINDIR]
SYSTEM_HOMES["nissrv.exe"] = [_DEFENDER, _OLD_DEFENDER, winsys.WINDIR]
KERNEL_NAMES = {"system", "registry", "memcompression", "secure system", "system idle process", "vmmem",
                "vmmemwsl"}


class AIError(Exception):
    """Something went wrong talking to the AI. The message is meant for the user."""


# ------------------------------------------------------------ config ---

def app_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    path = os.path.join(base, "Ramwise")
    if not os.path.isdir(path):
        old = os.path.join(base, "RAMCheck")  # the app's earlier name: take settings and keys along
        if os.path.isdir(old):
            try:
                os.replace(old, path)
            except OSError:
                pass
    os.makedirs(path, exist_ok=True)
    return path


CONFIG_PATH = os.path.join(app_dir(), "config.json")
SETUP_PATH = os.path.join(app_dir(), "my_setup.txt")

SETUP_TEMPLATE = """# Your setup: what should the AI know about your PC?
# Lines starting with # are ignored. Write freely, one fact per line.
# Anything you list here as used will not be flagged as unnecessary.
#
# Examples (remove the #, adjust or delete):
# Liquid cooler NZXT Kraken, pump and fan curves run through NZXT CAM
# Headset ASUS ROG Delta S, EQ is set in Armoury Crate
# Corsair RAM with RGB controlled by iCUE
# I play VR with a Meta Quest, the Oculus services are needed
# Overclocking is set in the BIOS, I don't need Windows OC tools
# I don't use OneDrive
"""


# ------------------------------------------------ protected API keys ---
# On Windows, keys are encrypted with DPAPI: only your Windows account on this PC can read them.
# Copying config.json to another PC or user gives nothing usable.

def _dpapi(data, protect):
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = Blob()
    descr = ctypes.c_wchar_p("Ramwise") if protect else None
    if not fn(ctypes.byref(blob_in), descr, None, None, None, 0x1, ctypes.byref(blob_out)):  # 0x1 = no UI
        raise OSError("DPAPI failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def _protect(text):
    return base64.b64encode(_dpapi(text.encode(), True)).decode()


def _unprotect(token):
    return _dpapi(base64.b64decode(token), False).decode()


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, json.JSONDecodeError):
        pass
    plain_on_disk = bool(cfg.get("api_keys")) and os.name == "nt"
    keys = dict(cfg.get("api_keys") or {})
    for provider, token in (cfg.pop("api_keys_protected", None) or {}).items():
        try:
            keys.setdefault(provider, _unprotect(token))
        except Exception:
            pass  # saved by another Windows user or PC, can't be read here
    cfg["api_keys"] = keys
    cfg["keep"] = list(cfg.get("keep") or [])  # own copies, never the shared default objects
    for k in ("models", "urls", "api_keys"):
        cfg[k] = dict(cfg.get(k) or {})
    # settings from earlier versions
    if cfg.get("api_key"):
        cfg["api_keys"].setdefault("claude", cfg.pop("api_key"))
    if cfg.get("claude_model"):
        cfg["models"].setdefault("claude", cfg.pop("claude_model"))
    if cfg.get("ollama_model"):
        cfg["models"].setdefault("ollama", cfg.pop("ollama_model"))
    if cfg.get("ollama_host"):
        cfg["urls"].setdefault("ollama", cfg.pop("ollama_host"))
    if cfg.get("provider") not in PROVIDERS:
        cfg["provider"] = "claude"
    if plain_on_disk or cfg.get("api_key"):
        try:
            save_config(cfg)  # keys from an older version: store them encrypted right away
        except OSError:
            pass
    return cfg


def save_config(cfg):
    data = dict(cfg)
    data.pop("api_key", None)
    if os.name == "nt" and data.get("api_keys"):
        try:
            data["api_keys_protected"] = {p: _protect(k) for p, k in data["api_keys"].items() if k}
            data.pop("api_keys")
        except Exception:
            pass  # encryption unavailable: fall back to plain text rather than losing the key
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CONFIG_PATH)  # never leaves a half-written config behind


def resolve_api_key(cfg, provider=None):
    """Returns (key, where it came from) or (None, None)."""
    p = provider or cfg["provider"]
    env_name = PROVIDERS[p]["env"]
    if env_name and os.environ.get(env_name):
        return os.environ[env_name], "environment"
    if cfg.get("api_keys", {}).get(p):
        return cfg["api_keys"][p], "saved"
    return None, None


def model_for(cfg, provider=None):
    p = provider or cfg["provider"]
    return cfg["models"].get(p) or (PROVIDERS[p]["models"] or [""])[0]


def url_for(cfg, provider=None):
    p = provider or cfg["provider"]
    return (cfg["urls"].get(p) or PROVIDERS[p]["url"]).rstrip("/")


def needs_key(provider):
    return PROVIDERS[provider]["where"] == "cloud" and provider != "custom"


def _version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def update_status():
    """{'state': 'update'|'current'|'error', 'version', 'url', 'error'}. Only reads the public release list."""
    api = REPO_URL.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"
    try:
        data = _get_json(api, {"Accept": "application/vnd.github+json", "User-Agent": "Ramwise"}, timeout=8)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # no release published yet
            return {"state": "current", "version": VERSION, "url": REPO_URL + "/releases"}
        return {"state": "error", "error": f"GitHub answered with error {e.code}."}
    except Exception:
        return {"state": "error", "error": "Couldn't reach GitHub. Check your internet connection."}
    tag = str(data.get("tag_name", ""))
    url = data.get("html_url") or REPO_URL + "/releases"
    if tag and _version_tuple(tag) > _version_tuple(VERSION):
        name, body = str(data.get("name") or ""), str(data.get("body") or "")
        # A release counts as a security update when "[security]" is in its title or notes.
        # Those are always shown, even if the user skipped the version.
        security = "[security]" in (name + " " + body).lower()
        return {"state": "update", "version": tag.lstrip("vV"), "url": url, "name": name,
                "notes": release_notes_text(body), "security": security}
    return {"state": "current", "version": VERSION, "url": url}


def release_notes_text(body, max_lines=14):
    """Release notes from GitHub, as plain text for the update window."""
    lines = []
    for line in body.replace("\r", "").splitlines():
        line = re.sub(r"^#+\s*", "", line).replace("**", "").replace("`", "").replace("[security]", "").strip()
        line = re.sub(r"^\s*[-*]\s+", "\u2022 ", line)
        if line or (lines and lines[-1]):
            lines.append(line)
    while lines and (not lines[0] or lines[0].lower().rstrip(":") in ("what's new", "whats new", "changes")):
        lines.pop(0)  # the window has its own "What's new" heading
    text = "\n".join(lines).strip()
    if len(lines) > max_lines:
        text = "\n".join(lines[:max_lines]).rstrip() + "\n..."
    return text


def check_for_update():
    """The update_status() dict if a newer version exists, else None. Used for the check at start."""
    st = update_status()
    return st if st["state"] == "update" else None


SETUP_URL = REPO_URL + "/releases/latest/download/Ramwise-Setup.exe"
SUMS_URL = REPO_URL + "/releases/latest/download/SHA256SUMS.txt"


class UpdateError(Exception):
    pass


def download_update(progress=None):
    """Downloads the newest installer to the temp folder and checks it against the release's
    SHA256SUMS.txt. Returns the file path. Raises UpdateError with a readable message."""
    import hashlib
    import tempfile
    headers = {"User-Agent": "Ramwise"}
    try:
        with urllib.request.urlopen(urllib.request.Request(SUMS_URL, headers=headers), timeout=20) as r:
            sums = r.read().decode("ascii", "replace")
    except Exception:
        raise UpdateError("Couldn't download the checksum list from GitHub.")
    expected = next((line.split()[0].lower() for line in sums.splitlines()
                     if line.strip().endswith("Ramwise-Setup.exe")), None)
    if not expected:
        raise UpdateError("The release has no checksum for the installer, so it won't be installed automatically.")
    path = os.path.join(tempfile.gettempdir(), "Ramwise-Setup.exe")
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(urllib.request.Request(SETUP_URL, headers=headers), timeout=60) as r, \
                open(path, "wb") as f:
            total, done = int(r.headers.get("Content-Length") or 0), 0
            while True:
                block = r.read(256 * 1024)
                if not block:
                    break
                f.write(block)
                digest.update(block)
                done += len(block)
                if progress:
                    progress(done, total)
    except OSError:
        raise UpdateError("The download was interrupted. Try again.")
    if digest.hexdigest() != expected:
        try:
            os.remove(path)
        except OSError:
            pass
        raise UpdateError("The downloaded installer doesn't match its checksum, so it was deleted. Try again later.")
    return path


def install_after_exit(path):
    """Hands the update over to a small helper that waits until Ramwise has really closed, then runs
    the installer quietly (just a progress bar) and starts the new version. That way the installer
    never finds Ramwise still running, and there's only one window at a time."""
    import subprocess
    here = os.path.dirname(sys.executable).lower()
    all_users = here.startswith(os.environ.get("PROGRAMFILES", r"C:\Program Files").lower())
    args = ["/SILENT", "/SP-", "/SUPPRESSMSGBOXES", "/NORESTART", "/RESTARTAPP",
            "/ALLUSERS" if all_users else "/CURRENTUSER"]
    arg_list = ",".join(f"'{a}'" for a in args)
    safe_path = path.replace("'", "''")
    script = (f"Wait-Process -Id {os.getpid()} -Timeout 60 -ErrorAction SilentlyContinue; "
              f"Start-Process -FilePath '{safe_path}' -ArgumentList {arg_list}")
    flags = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED_PROCESS | NEW_PROCESS_GROUP | NO_WINDOW
    subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script],
                     creationflags=flags, close_fds=True)


LOG_PATH = os.path.join(app_dir(), "error.log")


def log_error(text):
    """Appends to error.log (kept small) so problems can be reported with details."""
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 200_000:
            os.replace(LOG_PATH, LOG_PATH + ".old")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n--- {dt.datetime.now():%Y-%m-%d %H:%M:%S}, Ramwise {VERSION}, {install_mode()}, "
                    f"Python {sys.version.split()[0]}, {sys.platform}\n{text}\n")
    except OSError:
        pass


def install_mode():
    """'installed' (via the setup), 'portable' (single exe) or 'source'."""
    if not getattr(sys, "frozen", False):
        return "source"
    here = os.path.dirname(sys.executable)
    return "installed" if os.path.exists(os.path.join(here, "unins000.exe")) else "portable"


def ensure_setup_file():
    if not os.path.exists(SETUP_PATH):
        with open(SETUP_PATH, "w", encoding="utf-8") as f:
            f.write(SETUP_TEMPLATE)
        return True
    return False


def read_setup_text():
    ensure_setup_file()
    with open(SETUP_PATH, encoding="utf-8") as f:
        return f.read()


def write_setup_text(text):
    with open(SETUP_PATH, "w", encoding="utf-8") as f:
        f.write(text)


def setup_lines(text=None):
    text = read_setup_text() if text is None else text
    return [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]


# ----------------------------------------------------------- windows ---

def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(extra_args=""):
    """Starts a new elevated copy of this program. Returns True if Windows accepted."""
    try:
        import ctypes
        if getattr(sys, "frozen", False):
            exe, params = sys.executable, extra_args
        else:
            exe = sys.executable.replace("python.exe", "pythonw.exe")
            params = f'"{os.path.abspath(sys.argv[0])}" {extra_args}'
        return ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1) > 32
    except Exception:
        return False


# --------------------------------------------------------- measuring ---

def redact(path):
    """Strip the username from paths before they are sent to an AI."""
    if not path:
        return ""
    home = os.path.expanduser("~")
    if home and path.lower().startswith(home.lower()):
        path = "%USERPROFILE%" + path[len(home):]
    user = getpass.getuser()
    if user:
        path = re.sub(re.escape(user), "<user>", path, flags=re.IGNORECASE)
    return path


def _process_memory(proc, fast):
    """Close to the Task Manager value: USS (private memory), falls back to RSS."""
    if not fast:
        try:
            return proc.memory_full_info().uss
        except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError, OSError):
            pass
    return proc.memory_info().rss


def collect(fast=False, min_mb=0):
    """All running programs, grouped by name, biggest first."""
    groups = defaultdict(lambda: {"mem": 0, "count": 0, "exe": "", "protected": False, "pids": []})
    me = os.getpid()
    # a single-file exe runs as two processes (unpacker + app), skip both copies of Ramwise
    own_name = os.path.basename(sys.executable).lower() if getattr(sys, "frozen", False) else None
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if proc.pid in (0, me) or (own_name and (proc.info["name"] or "").lower() == own_name):
                continue
            name = proc.info["name"]
            protected = not name
            if protected:
                name = f"[protected] PID {proc.pid}"
            key = name.lower()
            g = groups[key]
            g["key"] = key
            g["name"] = name
            g["protected"] = protected
            g["mem"] += _process_memory(proc, fast)
            g["count"] += 1
            g["pids"].append(proc.pid)
            if not g["exe"] and proc.info["exe"]:
                g["exe"] = proc.info["exe"]
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    result = [g for g in groups.values() if g["mem"] / MB >= min_mb]
    result.sort(key=lambda g: g["mem"], reverse=True)
    return result


def memory_status():
    vm = psutil.virtual_memory()
    used = vm.total - vm.available
    return {"total": vm.total, "used": used, "available": vm.available,
            "percent": used / vm.total * 100 if vm.total else 0}


def can_end(group, verdict=None):
    """Whether offering 'End process' is reasonable at all."""
    if group.get("protected") or group["key"] in CRITICAL:
        return False
    if verdict and verdict.get("category") == "system":
        return False
    return True


def end_group(group):
    """Asks every process of the group to close. Returns (closed, failed_messages)."""
    procs, failed = [], []
    for pid in group["pids"]:
        try:
            p = psutil.Process(pid)
            p.terminate()
            procs.append(p)
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            failed.append(f"PID {pid}: access denied (try running as administrator)")
    gone, alive = psutil.wait_procs(procs, timeout=3)
    for p in alive:
        failed.append(f"PID {p.pid}: still running")
    return len(gone), failed


# ---------------------------------------------------------------- AI ---

SYSTEM_PROMPT = """You are a Windows expert helping a user find unnecessary programs that
use RAM. You get a list of running programs (grouped by name) with RAM usage, number of
processes, path, publisher and file description from the exe, whether it has an open window,
whether it is a Windows service, and whether it starts with Windows. You may also get notes
from the user about their setup.

Classify EVERY program with exactly one category:
- "system": part of Windows itself, never close (csrss, dwm, lsass, svchost, explorer ...)
- "important": drivers, security software, control software for hardware the user owns
  (cooling, RGB, audio, peripherals), and anything the user's setup says they use
- "in_use": something the user is clearly using right now. An open window is a strong sign.
- "optional": useful program that doesn't need to run all the time: tray launchers, updaters,
  sync tools, helpers that only matter when the main app is open
- "bloatware": provides nothing the user benefits from. Typical: OEM promo and "live" services,
  bundled trial software, ad or telemetry helpers, duplicate helpers of software the user
  already replaced. ALL of these must be true: no real function for this user, nothing they
  rely on breaks without it, and you know this specific program.
- "unknown": you don't recognize it. Always prefer this over guessing!

Confidence for every program:
- "high": you know this exact program and what it does
- "medium": you recognize the vendor or type but not this exact file
- "low": educated guess. Never combine "low" with "bloatware".

How to use the signals:
- Publisher and description are the most reliable hint about what a file is. Trust them over
  the file name. Missing publisher on an unknown exe is a reason for "unknown", not "bloatware".
- An open window means the user is probably using it right now: never "bloatware".
- A service that starts automatically and only exists to update or promote the vendor's other
  software is a good candidate for "optional" or "bloatware".
- Programs from the same vendor are separate decisions. The main app being needed doesn't make
  its updater needed, and an updater being junk doesn't make the main app junk.

The user's setup overrides your assumptions, but apply it STRICTLY:
- A program only counts as needed because of the setup if a line clearly names that exact
  program or the device it controls. Copy that line into "setup_match".
- Updaters, "live" services, telemetry and promo helpers are never covered by the setup.
- If a line says the user does NOT need something (e.g. "I don't need Windows OC tools"),
  programs of that kind are "optional" or "bloatware", and "setup_match" is that line.
- No clear match: "setup_match" is null.

More rules:
- If a tool controls cooling (pump, fan curves), hardware displays or audio EQs, say in the
  recommendation that settings may stop working without it.
- "[protected] PID ..." entries couldn't be read without admin rights. They are almost always
  protected system or security processes. Category "unknown", never suspicious.
- A Windows process name in the wrong folder IS suspicious (svchost.exe outside
  C:\\Windows\\System32). Say so.
- Don't recommend disabling Gaming Services or GameInput to save a few MB.
- Recommendations are concrete advice for the user: "Close it", "Turn off its autostart",
  "Uninstall it", "Turn off background activity in its settings", "Don't touch".
  Never write things like "Keep as bloatware", that's a verdict, not advice.
- Local AI engines (Ollama, LM Studio) and anything the user runs AI models with are tools
  the user chose to install: never "bloatware", at most "optional".
- The summary is honest: if plenty of RAM is free, cleaning up won't change much. Say so.
- English, casual and direct, no filler phrases, no em dashes.

Reply ONLY with JSON in this format, no markdown, no text before or after:
{
  "summary": "2-4 sentences overall assessment",
  "processes": [
    {
      "name": "exact program name from the list",
      "category": "system|important|in_use|optional|bloatware|unknown",
      "confidence": "high|medium|low",
      "what_is_it": "one sentence",
      "recommendation": "one sentence",
      "safe_to_close": true,
      "setup_match": "the setup line this is based on, or null"
    }
  ]
}"""

VERIFY_PROMPT = """You are double-checking another assessment of running Windows programs.
Your only job is to catch FALSE POSITIVES: programs that were marked "bloatware" or "optional"
but are actually needed. Closing a needed program is much worse than leaving some junk running.

For every program you get, decide the final category:
- Keep "bloatware" only if you are sure it gives this user nothing and nothing breaks without it.
- Downgrade "bloatware" to "optional" when it has some real use (updates, a feature some people
  use) or you are not completely sure.
- Change to "important" when it controls hardware (cooling, RGB, audio, input devices, GPU),
  is security software, or the user's setup names it.
- Change to "in_use" when it has an open window.
- Change to "unknown" when you don't really know what it is.
- Keep "optional" when it's fine to close and turn off its autostart.

Reply ONLY with JSON, no markdown:
{
  "reviews": [
    {
      "name": "exact program name",
      "category": "system|important|in_use|optional|bloatware|unknown",
      "confidence": "high|medium|low",
      "recommendation": "one sentence of advice for the user, e.g. 'Close it and turn off its autostart'. Never a sentence about the category itself.",
      "reason": "one short sentence why you kept or changed it"
    }
  ]
}"""


def enrich(procs, startup_by_key=None):
    """Adds publisher, description, window, service and autostart info to each program (Windows only)."""
    windows = winsys.visible_window_pids()
    svc = winsys.services_by_pid()
    if startup_by_key is None:
        startup_by_key = winsys.match_entries(winsys.startup_entries(), procs)
    for g in procs:
        info = winsys.file_info(g["exe"])
        g["company"] = info.get("company", "")
        g["description"] = info.get("description") or info.get("product", "")
        g["window"] = any(pid in windows for pid in g["pids"])
        g["services"] = [s["display"] or s["name"] for pid in g["pids"] for s in svc.get(pid, [])]
        g["autostart"] = [e["label"] for e in startup_by_key.get(g["key"], []) if e["enabled"]]
    return procs


def build_user_prompt(mem, procs, lines, keep=()):
    out = []
    if lines:
        out += ["User's setup (takes priority):"] + [f"- {l}" for l in lines] + [""]
    if keep:
        out += ["The user marked these programs as needed: " + ", ".join(keep), ""]
    out += [f"Total RAM: {mem['total'] / GB:.1f} GB, in use: {mem['percent']:.0f} %", "",
            "Programs (one per line, fields separated by |):"]
    for g in procs:
        path = redact(g["exe"]) or ("protected, not readable without admin rights"
                                    if g["protected"] else "path not readable")
        fields = [g["name"], f"{g['mem'] / MB:.0f} MB",
                  f"{g['count']} process{'es' if g['count'] != 1 else ''}", path]
        if g.get("company") or g.get("description"):
            fields.append(f"publisher: {g.get('company') or '?'}, description: {g.get('description') or '?'}")
        elif g.get("exe") and os.name == "nt":
            fields.append("no publisher info in the file")
        if g.get("window"):
            fields.append("has an open window")
        if g.get("services"):
            fields.append("service: " + ", ".join(sorted(set(g["services"]))[:3]))
        if g.get("autostart"):
            fields.append("starts with Windows")
        out.append(" | ".join(fields))
    return "\n".join(out)


def _post_json(url, payload, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ask_claude(prompt, model, api_key, system=SYSTEM_PROMPT):
    if not api_key:
        raise AIError("No API key yet. Add one in Settings, or switch to Ollama.")
    payload = {"model": model, "max_tokens": 8000, "system": system,
               "messages": [{"role": "user", "content": prompt}]}
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    try:
        data = _post_json(API_URL, payload, headers, timeout=180)
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:
            detail = ""
        hints = {
            400: "The API rejected the request",
            401: "The API key is invalid or was deleted. Enter a new one in Settings",
            403: "This key has no permission. Check it in the Anthropic Console",
            404: "That model name doesn't exist. Check the model in Settings",
            429: "Rate limit reached. Wait a moment and try again",
            529: "Anthropic is overloaded right now. Try again in a few minutes",
        }
        msg = hints.get(e.code, f"API error {e.code}")
        raise AIError(f"{msg}." + (f" ({detail})" if detail else ""))
    except OSError as e:
        raise AIError(f"Can't reach the Claude API. Check your internet connection. ({e})")
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def ask_ollama(prompt, model, host, system=SYSTEM_PROMPT, json_mode=True):
    if not model:
        raise AIError("No Ollama model chosen. Download one in Settings.")
    payload = {"model": model, "stream": False, "options": {"num_ctx": 16384, "temperature": 0.2}}
    if json_mode:
        payload["format"] = "json"
    else:
        payload["keep_alive"] = "2m"  # stays loaded briefly for follow-up questions, then frees the RAM
    payload.update({"messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": prompt}]})
    try:
        return _post_json(f"{host.rstrip('/')}/api/chat", payload, {}, timeout=600)["message"]["content"]
    except urllib.error.HTTPError as e:
        raise AIError(f"Ollama answered with error {e.code}. Is the model pulled? "
                      f"Run: ollama pull {model}")
    except OSError:
        raise AIError(f"Can't reach Ollama at {host}. Start Ollama and run: ollama pull {model}")


def _http_error(e, provider_name):
    try:
        body = json.loads(e.read())
        err = body.get("error", body)
        detail = err.get("message", "") if isinstance(err, dict) else str(err)
    except Exception:
        detail = ""
    hints = {
        400: f"{provider_name} rejected the request",
        401: f"The {provider_name} API key is invalid or was deleted. Enter a new one in Settings",
        402: f"Not enough credit on your {provider_name} account",
        403: f"This key has no permission for that. Check it at {provider_name}",
        404: "That model name doesn't exist (anymore). Click Load models in Settings and pick one",
        429: f"Rate limit or quota reached at {provider_name}. Wait a moment or check your plan",
        500: f"{provider_name} had a server error. Try again",
        503: f"{provider_name} is overloaded right now. Try again in a few minutes",
    }
    msg = hints.get(e.code, f"{provider_name} answered with error {e.code}")
    return AIError(f"{msg}." + (f" ({detail[:200]})" if detail else ""))


def ask_openai(prompt, model, url, api_key, system=SYSTEM_PROMPT, provider_name="The API"):
    """Any OpenAI-compatible chat API: OpenAI, Gemini, OpenRouter, Mistral, LM Studio, Groq ..."""
    if not url:
        raise AIError("No address set. Enter the API address in Settings.")
    if not model:
        raise AIError("No model chosen. Pick one in Settings (Load models shows what's available).")
    # no max_tokens / temperature on purpose: newer reasoning models reject them
    payload = {"model": model, "messages": [{"role": "system", "content": system},
                                            {"role": "user", "content": prompt}]}
    headers = {"X-Title": "Ramwise", "HTTP-Referer": REPO_URL}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        data = _post_json(f"{url}/chat/completions", payload, headers, timeout=300)
    except urllib.error.HTTPError as e:
        raise _http_error(e, provider_name)
    except OSError as e:
        raise AIError(f"Can't reach {provider_name} at {url}. ({e})")
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise AIError(f"{provider_name} sent an answer Ramwise doesn't understand.")
    if isinstance(content, list):  # some APIs split the answer into parts
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content or ""


def _get_json(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


_NOT_CHAT = ("embed", "tts", "whisper", "dall-e", "audio", "image", "moderation", "transcribe",
             "realtime", "search", "computer-use", "davinci", "babbage", "sora", "aqa")


def list_models(cfg, provider=None):
    """Current model names from the provider. Raises AIError with a readable message."""
    p = provider or cfg["provider"]
    info, url = PROVIDERS[p], url_for(cfg, p)
    key, _ = resolve_api_key(cfg, p)
    name = info["name"]
    try:
        if info["api"] == "anthropic":
            if not key:
                raise AIError("Save an API key first.")
            data = _get_json(f"{url}/models?limit=100", {"x-api-key": key, "anthropic-version": "2023-06-01"})
            return [m["id"] for m in data.get("data", [])]
        if info["api"] == "ollama":
            return sorted(m["name"] for m in _get_json(f"{url}/api/tags").get("models", []))
        if not url:
            raise AIError("Enter the API address first.")
        if needs_key(p) and not key:
            raise AIError("Save an API key first.")
        data = _get_json(f"{url}/models", {"Authorization": f"Bearer {key}"} if key else {})
        ids = [str(m.get("id", "")).removeprefix("models/") for m in data.get("data", [])]
        ids = [i for i in ids if i and not any(w in i.lower() for w in _NOT_CHAT)]
        return sorted(set(ids))
    except urllib.error.HTTPError as e:
        raise _http_error(e, name)
    except OSError:
        if info["where"] == "local":
            raise AIError(f"{name} isn't running. Start it and try again.")
        raise AIError(f"Can't reach {name}. Check your internet connection.")


def local_status(cfg, provider=None):
    """(running, text) for Ollama / LM Studio."""
    p = provider or cfg["provider"]
    try:
        models = list_models(cfg, p)
    except AIError:
        if p == "ollama":
            return False, "Ollama isn't running or isn't installed."
        return False, "LM Studio's local server isn't running. Open LM Studio, load a model and start the server."
    if not models:
        return True, ("Ollama is running, but no model is downloaded yet." if p == "ollama"
                      else "LM Studio is running, but no model is loaded.")
    return True, f"{PROVIDERS[p]['name']} is running with {len(models)} model{'s' if len(models) != 1 else ''}."


def ollama_unload(cfg):
    """Asks Ollama to drop the model from memory right away (it would otherwise stay loaded for minutes)."""
    try:
        _post_json(f"{url_for(cfg, 'ollama')}/api/generate", {"model": model_for(cfg, "ollama"), "keep_alive": 0},
                   {}, timeout=10)
    except Exception:
        pass


def ollama_pull(cfg, model, progress):
    """Downloads a model through Ollama. progress(text) is called along the way."""
    req = urllib.request.Request(f"{url_for(cfg, 'ollama')}/api/pull",
                                 data=json.dumps({"model": model, "stream": True}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3600) as r:
            for raw in r:
                line = json.loads(raw.decode() or "{}")
                if line.get("error"):
                    raise AIError(f"Ollama: {line['error']}")
                total, done = line.get("total"), line.get("completed")
                if total and done:
                    progress(f"Downloading {model} ... {done / total * 100:.0f} % of {total / GB:.1f} GB")
                elif line.get("status"):
                    progress(f"{model}: {line['status']}")
    except urllib.error.HTTPError as e:
        raise AIError(f"Ollama answered with error {e.code}. Check the model name.")
    except OSError:
        raise AIError("Can't reach Ollama. Is it running?")


def parse_json(text):
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AIError("The AI didn't answer in the expected format. Try again.")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        raise AIError("The AI's answer was cut off or broken. Try again, or assess fewer programs.")


def _ask(cfg, api_key, prompt, system, json_mode=True):
    p = cfg["provider"]
    api = PROVIDERS[p]["api"]
    if api == "ollama":
        return ask_ollama(prompt, model_for(cfg), url_for(cfg), system, json_mode)
    if api == "anthropic":
        return ask_claude(prompt, model_for(cfg), api_key, system)
    return ask_openai(prompt, model_for(cfg), url_for(cfg), api_key, system, PROVIDERS[p]["name"])


def _adjust(v, category, reason, **extra):
    if v.get("category") != category:
        v["adjusted"] = reason
    v["category"] = category
    v.update(extra)


def apply_rules(verdicts, procs, keep=(), engine=()):
    """Hard safety rules that override the AI, no matter what it said."""
    keep = {k.lower() for k in keep}
    engine = set(engine)
    for g in procs:
        v = verdicts.get(g["key"])
        if not v:
            continue
        v.setdefault("confidence", "medium")
        name, path = g["key"], (g.get("exe") or "").lower()
        if name in engine:
            _adjust(v, "important", "Ramwise uses this program for its AI analysis.", confidence="high",
                    safe_to_close=False, what_is_it=v.get("what_is_it") or "Runs the local AI model.",
                    recommendation="Ramwise needs it for the analysis. It releases the model's memory "
                                   "shortly after each analysis, so it's small the rest of the time.")
        elif name in keep:
            _adjust(v, "important", "You marked this as needed.", confidence="high",
                    setup_match="You marked this as needed in Ramwise", safe_to_close=False,
                    recommendation="You marked this as needed, so Ramwise leaves it alone.")
        elif name in SYSTEM_HOMES and path and not any(path.startswith(h) for h in SYSTEM_HOMES[name]):
            _adjust(v, "unknown", "Named like a Windows process, but runs from an unusual folder.",
                    suspicious=True, safe_to_close=False, confidence="high",
                    what_is_it="Uses the name of a Windows process but doesn't run from the Windows folder.",
                    recommendation="Scan it with Windows Security (Virus & threat protection) and check its location.")
        elif (name in SYSTEM_HOMES or name in KERNEL_NAMES) and v["category"] != "important":
            _adjust(v, "system", "Verified Windows component (name and folder match).", safe_to_close=False)
        elif g.get("protected") and v["category"] in ("bloatware", "optional"):
            _adjust(v, "unknown", "Can't be identified without admin rights.")
        elif name in CRITICAL and v["category"] in ("bloatware", "optional"):
            _adjust(v, "system", "Windows needs this to run.", safe_to_close=False)
        if v["category"] == "bloatware" and v.get("confidence") == "low":
            _adjust(v, "unknown", "Too uncertain to call it bloatware.")
        if v["category"] == "bloatware" and g.get("window") and v.get("confidence") != "high":
            _adjust(v, "optional", "Has an open window, so you might be using it.")
    return verdicts


def engine_keys(cfg):
    return ENGINE_PROCESSES.get(cfg.get("provider"), set())


_META = re.compile(r"^(keep|leave|mark|stays?|remains?|classif|categor|change|downgrade|upgrade)\b.*"
                   r"\b(bloatware|optional|unknown|important|in_use|system|category|verdict)\b", re.I)


def _meta_talk(text):
    """Smaller models sometimes answer 'Keep as bloatware.' instead of advice. Those get dropped."""
    return bool(_META.match(text)) or len(text.split()) < 3


def double_check(verdicts, procs, mem, cfg, api_key, lines, keep=()):
    """Second AI pass over everything marked bloatware or optional. Returns number of changes."""
    by_key = {g["key"]: g for g in procs}
    flagged = [by_key[k] for k, v in verdicts.items()
               if v["category"] in ("bloatware", "optional") and k in by_key and not v.get("adjusted")]
    if not flagged:
        return 0
    rows = []
    for g in flagged:
        v = verdicts[g["key"]]
        rows.append(f"{build_user_prompt(mem, [g], [], ()).splitlines()[-1]} || first verdict: "
                    f"{v['category']} ({v.get('confidence', '?')}), {v.get('what_is_it', '')}")
    prompt = "\n".join((["User's setup:"] + [f"- {l}" for l in lines] + [""] if lines else [])
                       + ["Programs to review:"] + rows)
    data = parse_json(_ask(cfg, api_key, prompt, VERIFY_PROMPT))
    changed = 0
    for r in data.get("reviews", []):
        key = str(r.get("name", "")).strip().lower()
        v = verdicts.get(key)
        new = r.get("category")
        if not v or new not in CATEGORIES:
            continue
        if new != v["category"]:
            changed += 1
            v["adjusted"] = f"Changed from {CATEGORIES[v['category']].lower()} on a second check: {r.get('reason', '')}".strip()
            v["category"] = new
        else:
            v["checked"] = r.get("reason", "")
        rec = str(r.get("recommendation") or "").strip()
        if rec and not _meta_talk(rec):
            v["recommendation"] = rec
        if r.get("confidence") in ("high", "medium", "low"):
            v["confidence"] = r["confidence"]
    apply_rules(verdicts, procs, keep, engine_keys(cfg))  # rules always get the last word
    return changed


def analyze(procs, mem, cfg, api_key=None, lines=None, startup_by_key=None, progress=None):
    """Runs the AI. Returns (summary, {program key: verdict}, model used, note)."""
    lines = setup_lines() if lines is None else lines
    keep = cfg.get("keep", [])
    say = progress or (lambda _t: None)
    say("Collecting details")
    enrich(procs, startup_by_key)
    model = model_for(cfg)
    say(f"Asking {model}")
    prompt = build_user_prompt(mem, procs, lines, keep)
    try:
        data = parse_json(_ask(cfg, api_key, prompt, SYSTEM_PROMPT))
    except AIError as e:
        if "format" not in str(e) and "cut off" not in str(e):
            raise
        say("Answer was messy, asking once more")  # smaller local models sometimes add chatter
        data = parse_json(_ask(cfg, api_key, prompt + "\n\nReply with the JSON object only, nothing else.",
                               SYSTEM_PROMPT))
    verdicts = {}
    for p in data.get("processes", []):
        name = str(p.get("name", "")).strip()
        if not name:
            continue
        if p.get("category") not in CATEGORIES:
            p["category"] = "unknown"
        if p.get("confidence") not in ("high", "medium", "low"):
            p["confidence"] = "medium"
        if _meta_talk(str(p.get("recommendation") or "")):
            p["recommendation"] = ""
        verdicts[name.lower()] = p
    apply_rules(verdicts, procs, keep, engine_keys(cfg))
    note = ""
    if cfg.get("double_check", True):
        say("Double-checking bloatware verdicts")
        try:
            changed = double_check(verdicts, procs, mem, cfg, api_key, lines, keep)
            note = f"Second check changed {changed} verdict{'s' if changed != 1 else ''}."
        except AIError as e:
            note = f"Second check skipped: {e}"
    if cfg["provider"] == "ollama":
        ollama_unload(cfg)  # a RAM tool shouldn't leave a 5 GB model sitting in memory
    return data.get("summary", ""), verdicts, model, note


def cleanup_candidates(procs, verdicts, startup_by_key, keep=()):
    """Programs worth closing / removing from autostart, with a sensible default selection."""
    keep = {k.lower() for k in keep}
    out = []
    for g in procs:
        v = verdicts.get(g["key"])
        if not v or v["category"] not in ("bloatware", "optional") or g["key"] in keep:
            continue
        if not can_end(g, v) or v.get("suspicious"):
            continue
        entries = [e for e in startup_by_key.get(g["key"], []) if e["enabled"]]
        preselect = (v["category"] == "bloatware" and v.get("confidence") == "high"
                     and v.get("safe_to_close", True) and not g.get("window"))
        out.append({"group": g, "verdict": v, "startup": entries, "selected": preselect})
    order = {"bloatware": 0, "optional": 1}
    out.sort(key=lambda c: (order[c["verdict"]["category"]], -c["group"]["mem"]))
    return out


def run_cleanup(items, close=True, disable_autostart=True):
    """Does the actual work. Returns (closed programs, autostart entries turned off, problems)."""
    closed, disabled, problems = 0, 0, []
    admin = is_admin() or os.name != "nt"
    for c in items:
        g = c["group"]
        services = [e for e in c["startup"] if e["kind"] == "service"]
        if disable_autostart:
            for e in c["startup"]:
                if e["needs_admin"] and not admin:
                    problems.append(f"{e['name']}: needs admin rights")
                    continue
                ok, msg = winsys.set_startup_enabled(e, False)
                disabled += ok
                if not ok:
                    problems.append(msg)
        if close:
            if services and not admin:  # a service runs as SYSTEM, closing it needs admin anyway
                problems.append(f"{services[0]['name']}: needs admin rights")
                continue
            stopped = False
            for e in services:  # stop services properly, otherwise Windows restarts them
                ok, msg = winsys.stop_service(e["service"], e["name"])
                stopped |= ok
                if not ok:
                    problems.append(msg)
            n, failed = end_group(g)
            closed += 1 if (n or stopped) else 0
            problems += [f"{g['name']}: {f}" for f in failed]
    return closed, disabled, problems


# ------------------------------------------------ questions per program ---

ASK_PROMPT = """You are the assistant inside Ramwise, a Windows tool that finds unnecessary programs.
The user asks about ONE specific program running on their PC. You get the facts Ramwise
collected about it and Ramwise's verdict.

- Answer concretely for this program in 2 to 6 sentences. Plain text, no markdown, no headings.
  Use short numbered steps only when the user asks how to do something.
- Answer in the language of the question.
- If you're not sure what the program is, say so and explain how to check (publisher, file
  location, searching the exact file name).
- Mention real risks when they apply: cooling and fan control, audio settings, drivers,
  anti-cheat for games, sync or backup tools.
- Never tell the user to turn off Windows security features or delete files in C:\\Windows."""


def ask_about(cfg, api_key, group, verdict, question, history=(), autostart=(), lines=None):
    """Answers a free question about one program. Returns plain text."""
    info = winsys.file_info(group.get("exe"))
    facts = [f"Program: {group['name']}",
             f"RAM: {group['mem'] / MB:.0f} MB in {group['count']} process{'es' if group['count'] != 1 else ''}",
             f"Location: {redact(group.get('exe')) or 'not readable'}"]
    if info:
        facts.append(f"Publisher: {info.get('company') or 'unknown'}, "
                     f"description: {info.get('description') or info.get('product') or 'none'}")
    if autostart:
        facts.append("Starts with Windows: " + ", ".join(autostart))
    if verdict:
        facts.append(f"Ramwise's verdict: {CATEGORIES[verdict['category']]} "
                     f"({verdict.get('confidence', 'medium')} confidence). {verdict.get('what_is_it', '')} "
                     f"Advice given: {verdict.get('recommendation', '')}")
    lines = setup_lines() if lines is None else lines
    if lines:
        facts.append("User's setup notes: " + "; ".join(lines))
    parts = ["\n".join(facts)]
    if history:
        parts.append("Earlier in this conversation:\n" + "\n".join(f"User: {q}\nYou: {a}" for q, a in history[-4:]))
    parts.append(f"Question: {question}")
    text = _ask(cfg, api_key, "\n\n".join(parts), ASK_PROMPT, json_mode=False)
    text = re.sub(r"\*\*|__|^#+\s*", "", text.strip(), flags=re.M)  # in case markdown slips through
    return text or "The AI returned an empty answer. Try asking differently."


# --------------------------------------------------------------- prices ---
# Current prices come from OpenRouter's public model list (it mirrors the providers' list prices).
# Cached for a week. Only a public list is downloaded, nothing about your PC is sent.

PRICE_URL = "https://openrouter.ai/api/v1/models"
PRICE_PATH = os.path.join(app_dir(), "prices.json")
PRICE_PREFIX = {"claude": "anthropic", "openai": "openai", "gemini": "google", "mistral": "mistralai"}
BUILTIN_PRICES = {"claude-haiku-4-5": (1.0, 5.0)}  # USD per million tokens (in, out), used when offline
REASONING_HINTS = ("gpt-5", "o1", "o3", "o4", "gemini-2.5", "gemini-3", "-r1", "thinking", "reason", "qwq",
                   "magistral")


def _norm_model(model):
    m = str(model).lower().split("/")[-1].split(":")[0]
    m = re.sub(r"-\d{8}$", "", m)  # date suffix like -20251001
    m = re.sub(r"-latest$", "", m)
    return m.replace(".", "-")


def load_prices(fetch=True, max_age_days=7):
    """{model id: (usd per M input, usd per M output)}. Uses the cache when it's fresh enough."""
    cached = {}
    try:
        with open(PRICE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cached = {k: tuple(v) for k, v in data.get("prices", {}).items()}
        if time.time() - data.get("time", 0) < max_age_days * 86400 or not fetch:
            return cached
    except (OSError, ValueError):
        if not fetch:
            return {}
    try:
        data = _get_json(PRICE_URL, {"User-Agent": "Ramwise"}, timeout=10)
        prices = {}
        for m in data.get("data", []):
            p = m.get("pricing") or {}
            try:
                pin, pout = float(p.get("prompt", 0)) * 1e6, float(p.get("completion", 0)) * 1e6
            except (TypeError, ValueError):
                continue
            if pin >= 0 and pout >= 0 and (pin or pout):
                prices[m["id"]] = (round(pin, 4), round(pout, 4))
        if prices:
            with open(PRICE_PATH, "w", encoding="utf-8") as f:
                json.dump({"time": time.time(), "prices": prices}, f)
            return prices
    except Exception:
        pass
    return cached


def price_for(provider, model, prices):
    """(usd per M in, usd per M out, source) or None if unknown. Local models cost nothing."""
    if PROVIDERS[provider]["where"] == "local":
        return 0.0, 0.0, "local"
    if not model:
        return None
    if provider == "openrouter" and model in prices:
        return (*prices[model], "OpenRouter")
    prefix, want = PRICE_PREFIX.get(provider), _norm_model(model)
    if prefix:
        family = [(mid, pr) for mid, pr in prices.items() if mid.startswith(prefix + "/")]
        for mid, (pin, pout) in family:
            if _norm_model(mid) == want:
                return pin, pout, "OpenRouter"
        if str(model).lower().endswith("-latest"):  # alias like mistral-small-latest: take the dearest match
            close = [pr for mid, pr in family if _norm_model(mid).startswith(want)]
            if close:
                pin, pout = max(close, key=lambda pr: pr[1])
                return pin, pout, "OpenRouter"
    for key, (pin, pout) in BUILTIN_PRICES.items():
        if want.startswith(key):
            return pin, pout, "built-in"
    return None


def is_reasoning(model):
    m = str(model).lower()
    return any(h in m for h in REASONING_HINTS)


def analysis_tokens(top, double_check):
    flagged = 0.25 * top if double_check else 0  # about a quarter usually gets re-checked
    tokens_in = 1500 + 45 * top + (900 + 60 * flagged if double_check else 0)
    tokens_out = 60 + 75 * top + 60 * flagged
    return tokens_in, tokens_out


def cost_range(tokens_in, tokens_out, price, model):
    """(low, high) in USD for one call. Reasoning models bill hidden thinking, so the range goes up."""
    pin, pout = price[0], price[1]
    cost = tokens_in * pin / 1e6 + tokens_out * pout / 1e6
    return cost * 0.7, cost * (3.5 if is_reasoning(model) else 1.4)


def format_usd(lo, hi):
    if hi <= 0:
        return "free"
    if hi < 0.01:
        return "less than 1 cent"
    if hi < 1:
        a, b = max(1, round(lo * 100)), max(1, round(hi * 100))
        return "about 1 cent" if a == b == 1 else (f"about {a} cents" if a == b else f"about {a} to {b} cents")
    return f"about ${lo:.2f} to ${hi:.2f}"


LAST_PATH = os.path.join(app_dir(), "last_analysis.json")


def save_last_analysis(summary, verdicts, model, note, keys):
    """Kept for an hour, so restarting as admin doesn't cost a new analysis."""
    clean = {k: {kk: vv for kk, vv in v.items() if kk != "_before"} for k, v in verdicts.items()}
    try:
        with open(LAST_PATH, "w", encoding="utf-8") as f:
            json.dump({"time": time.time(), "summary": summary, "verdicts": clean, "model": model,
                       "note": note, "keys": sorted(keys)}, f)
    except OSError:
        pass


def load_last_analysis(max_age=3600):
    try:
        with open(LAST_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data["time"] < max_age:
            return data
    except (OSError, ValueError, KeyError):
        pass
    return None


def savings(procs, verdicts):
    return sum(g["mem"] for g in procs
               if verdicts.get(g["key"], {}).get("category") in ("bloatware", "optional"))


def setup_fingerprint(lines):
    return hashlib.sha1("\n".join(lines).encode()).hexdigest()[:10]


# ------------------------------------------------------------ report ---

def build_markdown(summary, verdicts, procs, mem, model=""):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    cell = lambda s: str(s or "").replace("|", "/").replace("\n", " ")
    by_key = {g["key"]: g for g in procs}
    out = [f"# RAM report {stamp}", "",
           f"RAM in use: {mem['used'] / GB:.1f} of {mem['total'] / GB:.1f} GB ({mem['percent']:.0f} %)",
           f"Assessed by: {model}" if model else "", "", summary, "",
           f"Possible savings (bloatware + optional): about {savings(procs, verdicts) / MB:.0f} MB", ""]
    for cat, label in CATEGORIES.items():
        items = [(k, v) for k, v in verdicts.items() if v.get("category") == cat]
        if not items:
            continue
        items.sort(key=lambda kv: by_key.get(kv[0], {}).get("mem", 0), reverse=True)
        out += [f"## {label}", "", "| Process | RAM | What it is | Recommendation |", "|---|---|---|---|"]
        for key, v in items:
            m = by_key.get(key, {}).get("mem", 0) / MB
            rec = v.get("recommendation", "") + (f" ({v['adjusted']})" if v.get("adjusted") else "")
            out.append(f"| {cell(v.get('name'))} | {m:.0f} MB | {cell(v.get('what_is_it'))} | {cell(rec)} |")
        out.append("")
    return "\n".join(out)


def default_report_folder():
    home = os.path.expanduser("~")
    for f in (os.path.join(home, "Documents"), os.path.join(home, "OneDrive", "Documents")):
        if os.path.isdir(f):
            return f
    return app_dir()
