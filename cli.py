"""
Ramwise in the terminal. Same analysis as the window app, printed as text.

    python cli.py                      uses the AI chosen in the app's settings
    python cli.py --provider ollama    local model via Ollama (also: claude, openai, gemini,
                                       openrouter, mistral, custom, lmstudio)
    python cli.py --provider none      RAM list only
    python cli.py --save               also save a markdown report
"""

import argparse
import datetime as dt
import getpass
import os
import sys

import core

FROZEN = getattr(sys, "frozen", False)
C = {"reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m", "red": "\033[91m",
     "yellow": "\033[93m", "green": "\033[92m", "blue": "\033[94m", "cyan": "\033[96m",
     "magenta": "\033[95m", "grey": "\033[90m"}
CAT_COLOR = {"bloatware": "magenta", "optional": "blue", "unknown": "yellow",
             "in_use": "cyan", "important": "green", "system": "grey"}
MB, GB = core.MB, core.GB


def die(msg):
    print(f"\n{C['red']}{msg}{C['reset']}")
    raise SystemExit(1)


def ask_key(cfg, provider):
    info = core.PROVIDERS[provider]
    print(f"\n{C['bold']}{info['name']} API key required{C['reset']}")
    if info["key_url"]:
        print(f"Create one at {info['key_url']}")
    print(f"{C['dim']}No key? Use a free local model with --provider ollama{C['reset']}\n")
    key = getpass.getpass("Paste your key (input stays hidden), then press Enter: ").strip()
    if not key:
        die("No key entered.")
    if input("Save the key for next time? [y/N] ").strip().lower().startswith("y"):
        cfg["api_keys"][provider] = key
        core.save_config(cfg)
        print(f"{C['dim']}Saved to {core.CONFIG_PATH}{C['reset']}")
    return key


def print_overview(mem, procs, top):
    bar_len = 40
    filled = int(bar_len * mem["percent"] / 100)
    color = "green" if mem["percent"] < 60 else "yellow" if mem["percent"] < 85 else "red"
    print(f"\n{C['bold']}Memory:{C['reset']} {mem['used'] / GB:.1f} / {mem['total'] / GB:.1f} GB "
          f"({mem['percent']:.0f} %)")
    print(f"{C[color]}{'█' * filled}{C['grey']}{'░' * (bar_len - filled)}{C['reset']}\n")
    print(f"{C['bold']}{'Program':<34}{'RAM':>10}{'Instances':>11}{C['reset']}")
    for g in procs[:top]:
        print(f"{g['name'][:33]:<34}{g['mem'] / MB:>8.0f} MB{g['count']:>11}")
    rest = procs[top:]
    if rest:
        print(f"{C['dim']}... plus {len(rest)} smaller programs ({sum(g['mem'] for g in rest) / MB:.0f} MB){C['reset']}")


def print_report(summary, verdicts, procs):
    mem_by = {g["key"]: g["mem"] for g in procs}
    print(f"\n{C['bold']}AI assessment{C['reset']}\n{summary}")
    for cat, label in core.CATEGORIES.items():
        items = [v for k, v in verdicts.items() if v["category"] == cat]
        if not items:
            continue
        items.sort(key=lambda v: mem_by.get(v["name"].lower(), 0), reverse=True)
        col = C[CAT_COLOR[cat]]
        print(f"\n{col}{C['bold']}■ {label}{C['reset']}  {C['dim']}{core.CATEGORY_HINT[cat]}{C['reset']}")
        for v in items:
            m = mem_by.get(v["name"].lower(), 0)
            print(f"  {C['bold']}{v['name']}{C['reset']}  {C['dim']}{m / MB:.0f} MB{C['reset']}")
            if cat != "system":
                print(f"    {v.get('what_is_it', '')}")
                print(f"    {col}→ {v.get('recommendation', '')}{C['reset']}")
                if v.get("setup_match"):
                    print(f"    {C['dim']}setup: \"{v['setup_match']}\"{C['reset']}")
                if v.get("adjusted"):
                    print(f"    {C['dim']}corrected: {v['adjusted']}{C['reset']}")
    print(f"\n{C['bold']}Possible savings (bloatware + optional): about "
          f"{core.savings(procs, verdicts) / MB:.0f} MB{C['reset']}")
    print(f"{C['dim']}The AI can be wrong. Look a process up before you uninstall anything.")
    print(f"To close bloatware and turn off its autostart in one go, use the window app.{C['reset']}")


def main(argv=None):
    os.system("")  # enables ANSI colours in the legacy Windows console
    cfg = core.load_config()
    ap = argparse.ArgumentParser(prog="Ramwise-cli", description="RAM analysis with AI assessment")
    ap.add_argument("--provider", choices=[*core.PROVIDERS, "none"], default=cfg["provider"])
    ap.add_argument("--model", help="model to use for this run")
    ap.add_argument("--top", type=int, default=cfg["top"], help="how many of the biggest programs to assess")
    ap.add_argument("--min-mb", type=float, default=cfg["min_mb"], help="ignore smaller processes")
    ap.add_argument("--fast", action="store_true", help="faster, values slightly higher than Task Manager")
    ap.add_argument("--save", action="store_true", help="also save the result as a markdown report")
    ap.add_argument("--setup", action="store_true", help="open the setup file and exit")
    ap.add_argument("--reset-key", action="store_true", help="enter a new API key")
    ap.add_argument("--cli", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if args.setup:
        core.ensure_setup_file()
        print(f"Setup file: {core.SETUP_PATH}")
        if hasattr(os, "startfile"):
            os.startfile(core.SETUP_PATH)
        return
    if core.ensure_setup_file():
        print(f"{C['cyan']}Tip: list the hardware and software you use in {core.SETUP_PATH} "
              f"and the AI will judge more accurately. Open it with --setup{C['reset']}")
    if os.name == "nt" and not core.is_admin():
        print(f"{C['dim']}Note: some system processes can't be read without admin rights.{C['reset']}")

    key = None
    if args.provider != "none":
        key = None if args.reset_key else core.resolve_api_key(cfg, args.provider)[0]
        if not key and core.needs_key(args.provider):
            key = ask_key(cfg, args.provider)

    print(f"{C['dim']}Measuring processes ...{C['reset']}", end="\r")
    mem = core.memory_status()
    procs = core.collect(args.fast, args.min_mb)
    print_overview(mem, procs, args.top)
    if args.provider == "none":
        return

    run_cfg = dict(cfg, provider=args.provider)
    if args.model:
        run_cfg["models"] = dict(cfg["models"], **{args.provider: args.model})
    top = procs[:args.top]
    lines = core.setup_lines()
    extra = f", with {len(lines)} setup notes" if lines else ""
    print(f"\n{C['dim']}Asking {core.PROVIDERS[args.provider]['name']} ({core.model_for(run_cfg)}{extra}) "
          f"... can take 10-60 s{C['reset']}")
    try:
        summary, verdicts, model, note = core.analyze(top, mem, run_cfg, key, lines)
    except core.AIError as e:
        msg = str(e).replace("Enter a new one in Settings", "Enter a new one with --reset-key")
        die(msg)
    print_report(summary, verdicts, top)
    if note:
        print(f"{C['dim']}{note}{C['reset']}")

    if args.save:
        path = os.path.join(core.default_report_folder(), f"ram_report_{dt.datetime.now():%Y-%m-%d_%H-%M}.md")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(core.build_markdown(summary, verdicts, top, mem, model))
            print(f"\nReport saved: {path}")
        except OSError as e:
            print(f"\n{C['yellow']}Couldn't save the report ({e}){C['reset']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    finally:
        if FROZEN:
            try:
                input("\nPress Enter to close ...")
            except EOFError:
                pass
