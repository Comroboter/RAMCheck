"""
RAMCheck window app.
Everything that talks to the system or the AI lives in core.py, this file is only the interface.
"""

import collections
import re
import datetime as dt
import hashlib
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import urllib.parse
import webbrowser
from tkinter import filedialog, messagebox, ttk

import core
import hardware
import memtest
import winsys

# ---------------------------------------------------------------- look ---
# Night-sky palette: used memory glows cyan, the free part is a field of faint dots.
VOID = "#0c0a1c"      # window background
PANEL = "#15122b"     # list, detail panel, inputs
RAISED = "#221d42"    # hover
SELECT = "#2d2764"    # selected row
LINE = "#2b2652"
TEXT = "#ece9ff"
MUTED = "#8f89b8"
DIM = "#5d5788"
CYAN = "#3be3f2"
MAGENTA = "#ff3ea5"

# (main, alternate) so neighbouring blocks in the memory map stay distinguishable
CAT_COLORS = {
    "bloatware": ("#ff3ea5", "#cf2a86"),
    "optional":  ("#a07dff", "#7f5fe0"),
    "unknown":   ("#ffc857", "#d9a63c"),
    "in_use":    ("#3be3f2", "#1fb3c4"),
    "important": ("#4ee6a6", "#34b884"),
    "system":    ("#4a4380", "#3e3870"),
}
UNRATED = ("#3be3f2", "#1fb3c4")          # before any analysis
NOT_ASSESSED = ("#2c6570", "#245761")     # after an analysis, programs it skipped
SHARED_CELL = "#27224a"
MINT = "#4ee6a6"
MINT_DIM = "#2f8f6a"
ROW_COLORS = {"bloatware": MAGENTA, "optional": "#b99cff", "unknown": "#ffc857", "system": DIM}

SCALE = 1.0


def S(v):
    return int(round(v * SCALE))


# 64x64 PNG, used for the title bar and taskbar
ICON_PNG = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAK0UlEQVR42u2bW4glVxWGv7X3rnNOnT59SU9CnJmOpsPEmBAlD0mcEEVBI4KDiQlKvERFJSj4oG8+ig+i+KAIKoSIlyiKypAo+igYFbwQokYGEsdMnFs7jjM93afPrar2Xj5UnZ6+nDoX04NJ2xsOdJ/eq6vW2nv96//3qhIGDwv4/Mf99akp+05R3qFwh8ABoAEIL62hwJrCWYE/qvDzVsv/FJba2326PKTc+YV4KtaHReQTgtyEgGr/Oi/lIYjkt6nos6r6jVZHHoHTnUFBkEHON2r771ZjHzFiblFVQEPhuXkJrvygnRDy+xQjIgQNxyT4h9e6S7/dGgS7wdABfrp+3YcROWqQaxXNir+Zl4nz/UXt32sA9Qa5FpEPVqPZU0m6+nTha9gYAAv4ev3Ah4zYb4MWxriXidOjguEBK2Luc9HUC2nafLrwWaXv/HR88LCK+U2R433D3TSKNBZEwxuanTO/A6wBlIWFOMBjG3bEbnN+o082wGMsLMSAGiBMXeBjxthD5Dlv2b3DgmbG2ENTF/gYEGT//v311UvmryLm+qLQGXb3CCCiGl6YmQu3utVlOWKMWdS81I10XqwBGR0j9b5PHDbYWvIiPcxQc9stSGbHuSbgNYyRChqMmMXVZT3iROTewnY0wxHBN5sE0pGlwVSnEecuB0GErLmCkpXaKiAYbH1mk/MepZmujYH5hmlbG4eqKaAicq9DuF3zaiCjnA+9DrP3vI2pO29Hk3TgaooRfLvNxR/9hOziBSSq5KuaJsy/6wHqt7yGMNBWEReRnDzJxaNHc7w2Bh88sYl4+MBbuSZqFJxsuzdGLMfaZ/nxxT8RyUgYE0UF4XYHsjAK+cVafGuV2bfcw40//uFwmAxgGzDzxjdy/AMfQKwla17imoc+xOIjX0GTIaEOYKagsrDAmS98nsrMVbSyLo/c8CDv3/8W8L0hKaQgjpm/fYtvnPs1M64+LB0KX2XBAfVxtr6GhKk77gAL6T/PIy4anDWq+NWI+utei9t3NX75EmigcddhtKek5y/kWFCCGy6bo3H49Yg4fAjUbZU3NBbxaRMfEkxJ9DL1VCrTvHn6EF8/9+S47K3uJiFVmqagijiHOFsKYuJcniLrIChokoBIblsSAEQQY/K5G0ZPM6wYRExpAPJlFXrr7H0ycjBmDGQ0im+cO+z3CWxlAjYuEzL33V7z9wKwF4AdDYC+iNOgSWy3zJ3kqpPeoZtotrUQQn6DZQ6p5nO2gpkx49uay2cvUsBaUC3oqpY4rgRV7IQgOFEAQquFmTLIapTT3IGTAqZeh+VLaLdbOBMInQ6mYZCmK7cVwTQcmiSoZhgRepriNWBsFTJfWk0iBGyVVkgm2m22Es18dpwtKSaid+J5aos34ebnCc0modMldDobPm1Ct4tfa3L2i19i7Y9/wNRiUKH3/Anim1+HrceEtdZAW01TeidOcfqznyM9dw7rKvRCwpl0hTsbryLg6fmEXkjpbvh0QkJXA8daJ/nMqSdY9QlWzFjpII36wnjhEkHTBBTcNVdD0O2UVvOtrt0u2fJFTH0qXw0RtNdDnMPNz6MhDLQVa8gureS7JY7zwCO0Qo85GzNlq6gOvq6IcDFrkQRPzUSlqfLfB6DP1KzNGaHI9q3W/86YfF6WbcYAkcu2Q1hkP5XWt6kYMpQwQuo6sYgqYQIodJMiebZ66fKp8xBFZFyMVKuXg+Q92mmPFJ2KIrU4B9zCNgsZ3qeIyFCYT0lxrjIZuR1/BwiaJex78EEad70e7SUFwG3FCkPodPjXo9+kd+IEUq2Bz8ErPnIEu7gI2YBdoArWEc6do/P442ivB9aiwRNFMa88eBtRFOdyeICpMZa11r85ffaZna8CYi3Z2grz992fS9pusZCDFtMrdlqo33Ybz913X36DnQ7xe95N49OfQlut7YHbUEGk0UAaDda+/jVMYxrvU2469CYOvuIW0qyHlJwMqQYiVwXghZNPEUUFXuxICoiApsQ334wmIZe0UVSaJn7NUb3uOuzcPNnycn6hG25AWy10ZSXf3iUBwAfs9deDsWgIWOOox1fRS9qEkA3JzjwtG1P7JqJDk8thMcMlbV8OZ9nm05s0zVfe2vIAiOQn9Wm65V96REyOAUMwRERQ9VdYDv+3c1+M7UTsbk8O7wVgLwAvCTm8de6Lsb2CYyImKFEEIeSdmxJQE8grgLWb671zeZkLoRwQQ8hJ0ya1KAW6h6F1XVVR1VKe8OICULQMk5MnMVMGl87lLbJBU33ATjuSU6fwKyu5JkDx/zyHNBq5g2Vl0HtkdpZw/l8QPGIMWdojSdrMzR4gS7ulwVNVIlel013duBQ7EwD1HhvPcPHoUSoLCzQO31nSGSqUX5Kw9JWvErodTK2O1GK6jz+OaTSw178KsoyBks5awvnztL77GFKpoiFXg8/+/UnSrEvkytmdiKHVvsCpM3/GuUpBjHZaDariO2uIuOGyOWSIceuSFpFcDHW75avfXzWf5SJqva8ohJAR1GOGaPz81ChgTVQQJq5AAIrGhvqsnHAUggiRzXK43/QIw1dGjIGgm1awn9d9ujuMCYKOpQEmB8FiFUOng8TxwCbl+g7o9VDvkVptHdE1eLxPsSYqz00RfNoDBGMc/X6x93lD0Ro35KBDyHyCKTpIOx+AEJBqhcYnP4m7+TU5Xx+C5q3vfY/k979HajHqMypRzKsPvYl6PFeykjmCJ0mbZ//+K9rtS1gb4X3C7Mx+bly8G2v7Jz2DbdudSzx3/FckaQcRu3MgiLVoc5Xa2+8nfuB+dHl5uKKLYxof/zjLzzyDZIHMp1y3eBcHX3ELvaRV3NxgRTc3e4A06/KXY7/AEgHCocW7mZ9/JWnaHSKHPVfNHqDTXeG5408SRXYsOjEBD1BkdhZtt9cPK0pLpvdIpZKf7Kw2QYRKVCPNklzSShh4nIgqaZqjvYhBVTHGYW2FNO2hmhFUSmwDaZZQiWpXsC/g/frZ3lB1Z8y28/+cpMiGk/4BBGpd0uoW97T4fpitDLD9X8rhPTG0F4C9AOzJ4e1YPXbF2TnbnawCLlovcyOrhXObQFPEFpI1jJC0YRtPyG37clhLOUReaezEAWgz6kkxVRCLf+FEfiYwNze8vRXHJE89hTZXEesgS1lrXSBylXXWVuZE5Gq02heKQAiZT2l3lrlqdv8YfYEKa60LkxyMtqVRP/gsyKvJ+11mqFLLUqr33EN0663l3R0xaNKj88RPCUtnoXhQEmDhwGtpTF1NCH6gqTGGTrfJqTN/wvsMYwzhynSGCl/1OWnEB78vYt5bPCs8cv9ou83o3qAilRpE0SYsyLJkrBy1trJJ0qoGvE/HISrj9ga9IEY1/MCp6hMivG/cfSONxuUu8KA06H/ffxpkw4ii6hgnNbINJ0QsUeRG2k0ghQUQVX3i//5xebO0tNQG+bLkey6w+0fIfZUvLy0ttQ1gWvt4NAR/HMQx4OXCXTQ8iAvBH2/t41HWH8c6fbpj4KENzofdufXzIBh4iNOnO8D6sYlNsuYpFzX+YcTeX4BN2EV44AEjYkzAf6TVOfvzouJ5u4E/ujRtPl2NZv4BHJE8HbINqPlyXXVf+OIFPtpqn/lOQQA9W+p+AGySrj5dsVO/VJHDRsy1rL+BuV78Xy6vzpK/OmtMQI9J8A+sdc78jC2vzu69PF1Gxvg/eX3+P6baj/y+90qvAAAAAElFTkSuQmCC"


# ------------------------------------------------------------- widgets ---

# ----------------------------------------------------------- animation ---
# Motion only answers something the user did (hover, switch, analysis result).
# Respects Windows' "Animation effects" setting: off there means off here.

ANIMATE = True


def _read_motion_setting():
    global ANIMATE
    if os.name == "nt":
        try:
            import ctypes
            on = ctypes.c_int(1)
            ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0)  # SPI_GETCLIENTAREAANIMATION
            ANIMATE = bool(on.value)
        except Exception:
            pass


KEYBOARD = {"on": False}  # True after Tab was pressed, False after a mouse click


def focus_color(bg):
    return CYAN if KEYBOARD["on"] else bg


def is_focused(widget):
    # widget.focus_get() raises KeyError while a combobox list is open, so ask Tcl directly
    try:
        return str(widget.tk.call("focus")) == str(widget)
    except tk.TclError:
        return False


def ease(t):
    return 1 - (1 - t) ** 3  # ease-out cubic: quick start, soft landing


def tween(widget, key, ms, fn, done=None):
    """Calls fn(t) with t going 0..1 (eased) over ms. A new tween with the same key replaces the old one."""
    store = widget.__dict__.setdefault("_tweens", {})
    if key in store:
        try:
            widget.after_cancel(store.pop(key))
        except (tk.TclError, ValueError):
            pass
    if not ANIMATE or ms <= 0:
        fn(1.0)
        if done:
            done()
        return
    start = time.perf_counter()

    def step():
        t = min(1.0, (time.perf_counter() - start) * 1000 / ms)
        try:
            fn(ease(t))
        except tk.TclError:  # widget is gone
            store.pop(key, None)
            return
        if t < 1:
            store[key] = widget.after(15, step)
        else:
            store.pop(key, None)
            if done:
                done()
    step()


def _rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def fade_label(label, text, color, bg=None, hold_ms=None):
    """Sets a message with a short fade-in. With hold_ms it fades out again afterwards."""
    bg = bg or label.cget("bg")
    label.configure(text=text)
    token = label.__dict__["_msg"] = label.__dict__.get("_msg", 0) + 1
    tween(label, "fade", 220, lambda t: label.configure(fg=mix(bg, color, t)))
    if hold_ms:
        def out():
            if label.__dict__.get("_msg") == token:  # a newer message replaced this one
                tween(label, "fade", 500, lambda t: label.configure(fg=mix(color, bg, t)),
                      done=lambda: label.__dict__.get("_msg") == token and label.configure(text=""))
        label.after(hold_ms, out)


# ------------------------------------------------------------- widgets ---

class FlatButton(tk.Label):
    """A button we can actually colour on Windows (tk.Button ignores most colours there)."""

    STYLES = {
        "primary": (CYAN, VOID, "#86f1fa", VOID),
        "ghost":   (PANEL, TEXT, RAISED, TEXT),
        "quiet":   (VOID, MUTED, PANEL, TEXT),
        "danger":  (PANEL, MAGENTA, "#2c1438", MAGENTA),
        "alert":   (MAGENTA, VOID, "#ff7cc2", VOID),
    }

    def __init__(self, master, text, command=None, kind="ghost", font=None,
                 padx=14, pady=7, anchor="center"):
        bg, fg, self.bg_hover, self.fg_hover = self.STYLES[kind]
        parent_bg = master.cget("bg")
        # a button must stand out from what it sits on: on a panel, ghost buttons get a lighter face,
        # quiet ones take the surface colour so they don't show up as dark boxes
        if kind == "quiet":
            bg, self.bg_hover = parent_bg, mix(parent_bg, TEXT, 0.07)
        elif kind in ("ghost", "danger") and bg == parent_bg:
            bg = mix(parent_bg, TEXT, 0.07)
            self.bg_hover = mix(bg, MAGENTA if kind == "danger" else TEXT, 0.12 if kind == "danger" else 0.08)
        self.bg_normal, self.fg_normal = bg, fg
        self.bg_disabled = PANEL if kind in ("primary", "alert") else bg  # loud colours only when usable
        super().__init__(master, text=text, bg=bg, fg=fg, font=font, padx=S(padx), pady=S(pady),
                         cursor="hand2", takefocus=1, anchor=anchor, highlightthickness=1,
                         highlightbackground=master.cget("bg"), highlightcolor=CYAN)
        self.command = command
        self.enabled = True
        self.active = False
        self.hover = False
        self._now = (bg, fg)
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._click)
        self.bind("<Return>", self._click)
        self.bind("<space>", self._click)

    def _hover(self, on):
        self.hover = on
        self._paint(fast=False)

    def _target(self):
        if not self.enabled:
            return self.bg_disabled, DIM
        if self.hover or self.active:
            return self.bg_hover, self.fg_hover
        return self.bg_normal, self.fg_normal

    def _paint(self, fast=True):
        bg, fg = self._target()
        self.configure(cursor="hand2" if self.enabled else "arrow")
        start_bg, start_fg = self._now

        def step(t):
            self._now = (mix(start_bg, bg, t), mix(start_fg, fg, t))
            self.configure(bg=self._now[0], fg=self._now[1])
        tween(self, "paint", 0 if fast else 140, step)

    def _press(self, _e=None):
        if self.enabled:  # brief darker flash so a click feels registered
            self.configure(bg=mix(self._now[0], VOID, 0.25))

    def _click(self, _e=None):
        self._paint(fast=False)
        if self.enabled and self.command:
            self.command()

    def set_enabled(self, on):
        self.enabled = on
        self._paint()

    def set_active(self, on):
        self.active = on
        self._paint(fast=False)


class Tooltip:
    """Small hint that appears after hovering for a moment."""

    def __init__(self, widget, text, font):
        self.widget, self.text, self.font, self.tip, self.job = widget, text, font, None, None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None):
        self._hide()
        self.job = self.widget.after(550, self._show)

    def _show(self):
        w = self.widget
        if not w.winfo_exists():
            return
        self.tip = tk.Toplevel(w)
        self.tip.wm_overrideredirect(True)
        self.tip.configure(bg=LINE)
        tk.Label(self.tip, text=self.text, bg=RAISED, fg=TEXT, font=self.font, justify="left",
                 wraplength=S(280), padx=S(10), pady=S(6)).pack(padx=1, pady=1)
        self.tip.update_idletasks()
        x = w.winfo_rootx() + w.winfo_width() - self.tip.winfo_reqwidth()
        y = w.winfo_rooty() + w.winfo_height() + S(6)
        self.tip.geometry(f"+{max(0, x)}+{y}")

    def _hide(self, _e=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


class TabBar(tk.Frame):
    """Tabs with one indicator line that slides to the active tab."""

    def __init__(self, master, items, command, font):
        super().__init__(master, bg=VOID)
        self.labels, self.active, self.command = {}, None, command
        row = tk.Frame(self, bg=VOID)
        row.pack(anchor="w")
        for key, text in items:
            lbl = tk.Label(row, text=text, bg=VOID, fg=MUTED, font=font, padx=S(12), pady=S(10), cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, k=key: command(k))
            lbl.bind("<Enter>", lambda e, k=key: self._hover(k, True))
            lbl.bind("<Leave>", lambda e, k=key: self._hover(k, False))
            self.labels[key] = lbl
        self.line = tk.Canvas(self, height=S(2), bg=VOID, highlightthickness=0)
        self.line.pack(fill="x")
        self.bar = self.line.create_rectangle(0, 0, 0, S(2), fill=CYAN, width=0)
        self._x = (0, 0)

    def _hover(self, key, on):
        if key != self.active:
            lbl = self.labels[key]
            start = lbl.cget("fg")
            tween(lbl, "fg", 140, lambda t: lbl.configure(fg=mix(start, TEXT if on else MUTED, t)))

    def set(self, key):
        old = self.active
        self.active = key
        for k, lbl in self.labels.items():
            lbl.configure(fg=TEXT if k == key else MUTED)
        self.update_idletasks()
        lbl = self.labels[key]
        pad = S(12)
        x0, x1 = lbl.winfo_x() + pad, lbl.winfo_x() + lbl.winfo_width() - pad
        if x1 <= x0:  # not laid out yet
            self.after(30, lambda: self.set(key))
            return
        sx0, sx1 = self._x if old else (x0, x1)

        def step(t):
            a, b = sx0 + (x0 - sx0) * t, sx1 + (x1 - sx1) * t
            self.line.coords(self.bar, a, 0, b, S(2))
            self._x = (a, b)
        tween(self, "slide", 260, step)


class Segmented(tk.Canvas):
    """A row of options with a highlight that slides to the chosen one."""

    def __init__(self, master, options, command=None, font=None, value=None):
        self.options, self.command = options, command
        self.fnt = tkfont.Font(font=font)
        pad, h = S(14), S(32)
        self.widths = [self.fnt.measure(text) + 2 * pad for _, text in options]
        width = sum(self.widths) + S(6)
        bg = master.cget("bg")
        super().__init__(master, width=width, height=h, bg=bg, highlightthickness=1, highlightbackground=bg,
                         highlightcolor=bg, takefocus=1, cursor="hand2")
        self.create_rectangle(0, 0, width, h, fill=PANEL, width=0)
        self.pill = self.create_rectangle(0, 0, 0, 0, fill=SELECT, width=0)
        self.texts, self.spans, x = [], [], S(3)
        for (val, text), w in zip(options, self.widths):
            self.spans.append((x, x + w))
            self.texts.append(self.create_text(x + w / 2, h / 2, text=text, font=self.fnt, fill=MUTED))
            x += w
        self.value, self.hover = None, None
        self._pill = None
        self.bind("<Button-1>", self._click)
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<Left>", lambda e: self._step(-1))
        self.bind("<Right>", lambda e: self._step(1))
        self.bind("<FocusIn>", lambda e: self.configure(highlightcolor=focus_color(bg)))
        self.set(value if value is not None else options[0][0], animate=False)

    def _index_at(self, x):
        for i, (a, b) in enumerate(self.spans):
            if a <= x < b:
                return i
        return None

    def _motion(self, e):
        self._set_hover(self._index_at(e.x))

    def _set_hover(self, i):
        self.hover = i
        self._paint_text()

    def _paint_text(self):
        for i, (val, _) in enumerate(self.options):
            color = TEXT if val == self.value else (TEXT if i == self.hover else MUTED)
            self.itemconfigure(self.texts[i], fill=color)

    def _click(self, e):
        i = self._index_at(e.x)
        if i is not None:
            self.focus_set()
            self._choose(self.options[i][0])

    def _step(self, d):
        vals = [v for v, _ in self.options]
        i = max(0, min(len(vals) - 1, vals.index(self.value) + d))
        self._choose(vals[i])

    def _choose(self, value):
        if value != self.value:
            self.set(value)
            if self.command:
                self.command(value)

    def set(self, value, animate=True):
        self.value = value
        i = [v for v, _ in self.options].index(value)
        a, b = self.spans[i]
        h = int(self.cget("height"))
        target = (a, S(3), b, h - S(3))
        start = self._pill or target

        def step(t):
            box = tuple(s + (g - s) * t for s, g in zip(start, target))
            self.coords(self.pill, *box)
            self._pill = box
        tween(self, "pill", 240 if animate else 0, step)
        self._paint_text()

    def get(self):
        return self.value


class Switch(tk.Canvas):
    """On/off switch: a cell that slides across its track. Square on purpose, like the memory cells:
    Tk draws circles without edge smoothing on Windows, which made the round version look lumpy."""

    def __init__(self, master, on=False, command=None):
        self.w, self.h = S(36), S(20)
        bg = master.cget("bg")
        super().__init__(master, width=self.w, height=self.h, bg=bg, highlightthickness=1,
                         highlightbackground=bg, highlightcolor=bg, takefocus=1, cursor="hand2")
        self.track = self.create_rectangle(0, 0, self.w, self.h, width=0)
        self.knob = self.create_rectangle(0, 0, 0, 0, width=0)
        self.on, self.command, self._t = on, command, 1.0 if on else 0.0
        self._draw(self._t)
        self.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<space>", lambda e: self.toggle())
        self.bind("<Return>", lambda e: self.toggle())
        self.bind("<FocusIn>", lambda e: self.configure(highlightcolor=focus_color(bg)))
        self.bind("<Enter>", lambda e: self._draw(self._t, hover=True))
        self.bind("<Leave>", lambda e: self._draw(self._t))

    def _draw(self, t, hover=False):
        self._t = t
        track = mix(mix(LINE, "#1c6b75", t), TEXT, 0.06 if hover else 0)
        self.itemconfigure(self.track, fill=track)
        pad = S(3)
        d = self.h - 2 * pad
        x = pad + (self.w - 2 * pad - d) * t
        self.coords(self.knob, round(x), pad, round(x) + d, pad + d)
        self.itemconfigure(self.knob, fill=mix(MUTED, CYAN, t))

    def set(self, on, animate=True):
        self.on = on
        start, goal = self._t, 1.0 if on else 0.0
        tween(self, "knob", 180 if animate else 0, lambda t: self._draw(start + (goal - start) * t))

    def toggle(self):
        self.set(not self.on)
        if self.command:
            self.command(self.on)

    def get(self):
        return self.on


class StopSlider(tk.Frame):
    """Slider that snaps to sensible values, with the current value written next to it."""

    def __init__(self, master, stops, value, fmt, font, command=None):
        super().__init__(master, bg=master.cget("bg"))
        self.stops, self.fmt, self.command = stops, fmt, command
        self.idx = min(range(len(stops)), key=lambda i: abs(stops[i] - value))
        self.W, self.H = S(300), S(28)
        bg = self.cget("bg")
        self.c = tk.Canvas(self, width=self.W, height=self.H, bg=bg, highlightthickness=0, takefocus=1,
                           cursor="hand2")
        self.c.pack(side="left")
        self.label = tk.Label(self, text="", bg=bg, fg=TEXT, font=font, width=12, anchor="w")
        self.label.pack(side="left", padx=(S(14), 0))
        y, self.pad = self.H / 2, S(10)
        th = max(2, S(4))  # track thickness, whole pixels so it stays sharp
        self.ty0 = round(y - th / 2)
        self.ty1 = self.ty0 + th
        self.c.create_rectangle(self.pad, self.ty0, self.W - self.pad, self.ty1, fill=LINE, width=0)
        self.fill = self.c.create_rectangle(self.pad, self.ty0, self.pad, self.ty1, fill=CYAN, width=0)
        self.ticks = []
        tk_ = max(2, S(2))
        for i in range(len(stops)):
            x = round(self._x(i))
            self.ticks.append(self.c.create_rectangle(x - tk_ // 2, round(y) - tk_ // 2,
                                                      x - tk_ // 2 + tk_, round(y) - tk_ // 2 + tk_, width=0))
        self.ring = self.c.create_rectangle(0, 0, 0, 0, outline="", width=max(1, S(1.5)))
        self.knob = self.c.create_rectangle(0, 0, 0, 0, fill=TEXT, width=0)
        self.pos, self.r, self.hot = self._x(self.idx), S(6), False
        self._draw()
        self.c.bind("<Button-1>", self._drag)
        self.c.bind("<B1-Motion>", self._drag)
        self.c.bind("<ButtonRelease-1>", lambda e: self._snap())
        self.c.bind("<Enter>", lambda e: self._grow(True))
        self.c.bind("<Leave>", lambda e: self._grow(False))
        self.c.bind("<Left>", lambda e: self.set_index(self.idx - 1))
        self.c.bind("<Right>", lambda e: self.set_index(self.idx + 1))
        self.c.bind("<FocusIn>", lambda e: self._draw())
        self.c.bind("<FocusOut>", lambda e: self._draw())
        # the wheel router (App._wheel) asks this first, so the page doesn't scroll at the same time
        self.c._on_wheel = lambda up: self.set_index(self.idx + (1 if up else -1))

    def _x(self, i):
        return self.pad + (self.W - 2 * self.pad) * i / (len(self.stops) - 1)

    def _draw(self):
        y, x, r = round(self.H / 2), round(self.pos), round(self.r)
        self.c.coords(self.fill, self.pad, self.ty0, x, self.ty1)
        self.c.coords(self.knob, x - r, y - r, x + r, y + r)
        ring = r + S(3)
        self.c.coords(self.ring, x - ring, y - ring, x + ring, y + ring)
        self.c.itemconfigure(self.ring, outline=CYAN if is_focused(self.c) and KEYBOARD["on"] else "")
        for i, t in enumerate(self.ticks):
            self.c.itemconfigure(t, fill=VOID if self._x(i) <= x else DIM)
        self.label.configure(text=self.fmt(self.stops[self.idx]))

    def _grow(self, on):
        start, goal = self.r, S(7) if on else S(6)

        def step(t):
            self.r = start + (goal - start) * t
            self._draw()
        tween(self.c, "grow", 120, step)

    def _drag(self, e):
        self.c.focus_set()
        self.pos = max(self.pad, min(self.W - self.pad, e.x))
        idx = round((self.pos - self.pad) / (self.W - 2 * self.pad) * (len(self.stops) - 1))
        if idx != self.idx:
            self.idx = idx
            if self.command:
                self.command(self.get())
        self._draw()

    def _snap(self):
        start, goal = self.pos, self._x(self.idx)

        def step(t):
            self.pos = start + (goal - start) * t
            self._draw()
        tween(self.c, "snap", 160, step)

    def set_index(self, i, animate=True):
        i = max(0, min(len(self.stops) - 1, i))
        changed = i != self.idx
        self.idx = i
        start, goal = self.pos, self._x(i)

        def step(t):
            self.pos = start + (goal - start) * t
            self._draw()
        tween(self.c, "snap", 180 if animate else 0, step)
        if changed and self.command:
            self.command(self.get())

    def set(self, value, animate=False):
        self.set_index(min(range(len(self.stops)), key=lambda i: abs(self.stops[i] - value)), animate)

    def get(self):
        return self.stops[self.idx]


class Check(tk.Canvas):
    """Square checkbox we can colour (tk.Checkbutton looks out of place on a dark window)."""

    def __init__(self, master, checked=False, command=None):
        size = S(16)
        super().__init__(master, width=size, height=size, bg=master.cget("bg"), highlightthickness=0,
                         cursor="hand2")
        self.checked, self.command, self.size = checked, command, size
        self.bind("<Button-1>", lambda e: self.toggle())
        self.draw()

    def draw(self):
        self.delete("all")
        s = self.size
        if self.checked:
            self.create_rectangle(0, 0, s, s, fill=CYAN, width=0)
            # whole pixels and exact 45 degree legs, so the unsmoothed line still looks clean
            a, b = max(2, round(s * 0.19)), max(4, round(s * 0.34))
            x0, y0 = round(s * 0.22), round(s * 0.50)
            self.create_line(x0, y0, x0 + a, y0 + a, x0 + a + b, y0 + a - b, fill=VOID,
                             width=max(2, round(s / 8)), capstyle="projecting", joinstyle="miter")
        else:
            self.create_rectangle(1, 1, s - 1, s - 1, outline=MUTED, width=1)

    def toggle(self):
        self.checked = not self.checked
        self.draw()
        if self.command:
            self.command()


class PaddedEntry(tk.Entry):
    """Text field with breathing room inside (tk.Entry has no inner padding of its own).
    The entry sits in a bordered frame; placing the entry places the frame."""

    def __init__(self, parent, font, width=30, show=None):
        self.box = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        super().__init__(self.box, width=width, show=show, bg=PANEL, fg=TEXT, insertbackground=CYAN,
                         relief="flat", bd=0, font=font, highlightthickness=0,
                         disabledbackground=PANEL, disabledforeground=DIM)
        tk.Pack.pack_configure(self, fill="x", padx=S(10), pady=S(7))
        self.bind("<FocusIn>", lambda e: self.box.configure(highlightbackground=CYAN), add="+")
        self.bind("<FocusOut>", lambda e: self.box.configure(highlightbackground=LINE), add="+")
        self.bind("<Enter>", lambda e: self.focus_get is not None and self._hover(True), add="+")
        self.bind("<Leave>", lambda e: self._hover(False), add="+")
        self.box.bind("<Button-1>", lambda e: self.focus_set())  # clicking the padding focuses too

    def _hover(self, on):
        if not is_focused(self):
            self.box.configure(highlightbackground=DIM if on else LINE)

    @staticmethod
    def _clean(kw):
        kw.pop("ipady", None)
        kw.pop("ipadx", None)
        return kw

    def pack(self, **kw):
        self.box.pack(**self._clean(kw))

    def grid(self, **kw):
        self.box.grid(**self._clean(kw))

    pack_configure, grid_configure = pack, grid

    def pack_forget(self):
        self.box.pack_forget()

    def grid_remove(self):
        self.box.grid_remove()


def styled_entry(parent, font, width=30, show=None):
    return PaddedEntry(parent, font, width, show)



def hover_rows(tree):
    """Highlights the row under the mouse (Treeview can't do that by itself)."""
    tree.tag_configure("hover", background=RAISED)
    state = {"iid": None}

    def set_hover(iid):
        old = state["iid"]
        if old == iid:  # a refresh may have reset the row's tags, put the highlight back
            if iid and tree.exists(iid) and "hover" not in tree.item(iid, "tags"):
                tree.item(iid, tags=[*tree.item(iid, "tags"), "hover"])
            return
        if old and tree.exists(old):
            tree.item(old, tags=[t for t in tree.item(old, "tags") if t != "hover"])
        if iid:
            tree.item(iid, tags=[*tree.item(iid, "tags"), "hover"])
        state["iid"] = iid
    tree.bind("<Motion>", lambda e: set_hover(tree.identify_row(e.y) or None), add="+")
    tree.bind("<Leave>", lambda e: set_hover(None), add="+")


def scrollable(parent, bg, root):
    """A frame that scrolls vertically when its content is taller than the window."""
    outer = tk.Frame(parent, bg=bg)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
    sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=bg)
    win = canvas.create_window(0, 0, window=inner, anchor="nw")

    def relayout(_e=None):
        canvas.configure(scrollregion=(0, 0, inner.winfo_reqwidth(), inner.winfo_reqheight()))
        need = inner.winfo_reqheight() > canvas.winfo_height() > 1
        if need and not sb.winfo_ismapped():
            sb.pack(side="right", fill="y", before=canvas)
        elif not need and sb.winfo_ismapped():
            sb.pack_forget()
            canvas.yview_moveto(0)
    inner.bind("<Configure>", relayout)
    canvas.bind("<Configure>", lambda e: (canvas.itemconfigure(win, width=e.width), relayout()))

    def wheel(up):
        if sb.winfo_ismapped():
            canvas.yview_scroll(-3 if up else 3, "units")
    outer._on_wheel = wheel
    return outer, inner


def pick_family(root, *names):
    families = {f.lower(): f for f in tkfont.families(root)}
    for n in names:
        if n.lower() in families:
            return families[n.lower()]
    return tkfont.nametofont("TkDefaultFont").actual("family")


# ------------------------------------------------------------- presets ---

PRESETS = {
    "quick": {"name": "Quick", "top": 20, "refresh_s": 30, "min_mb": 25, "double_check": False,
              "desc": "Only the 20 biggest programs, no second check. Fastest and cheapest. Good for a quick "
                      "look, or when a local model does the work."},
    "balanced": {"name": "Balanced", "top": 40, "refresh_s": 10, "min_mb": 10, "double_check": True,
                 "desc": "Recommended for most PCs. Covers everything that uses a noticeable amount of RAM "
                         "and double-checks every bloatware verdict."},
    "thorough": {"name": "Thorough", "top": 70, "refresh_s": 5, "min_mb": 5, "double_check": True,
                 "desc": "Goes down to small background tools and updates more often. Takes longer and "
                         "costs a bit more, worth it for a big cleanup."},
}
CUSTOM_DESC = "Your own mix. Pick a preset to go back to a tested combination."


def _duration(lo, hi):
    """'20 to 45 seconds', '1 to 2.5 minutes': rounded, because these are estimates."""
    def secs(x):
        return max(5, int(5 * round(x / 5)))

    def mins(x):
        v = round(x / 30) / 2
        return f"{v:g}"
    if hi < 60:
        return f"{secs(lo)} to {secs(hi)} seconds"
    unit = "minute" if mins(hi) == "1" else "minutes"
    if lo < 60:
        return f"{secs(lo)} seconds to {mins(hi)} {unit}"
    return f"{mins(lo)} to {mins(hi)} {unit}"


def estimate_text(top, double_check, provider, model, prices):
    """Rough time and cost per analysis for the chosen model. Deliberately given as ranges."""
    tokens_in, tokens_out = core.analysis_tokens(top, double_check)
    if core.PROVIDERS[provider]["where"] == "local":
        # typical 25-60 tokens/s for a 7-8B model on a gaming GPU
        return (f"Free. Rough estimate on a fast graphics card: {_duration(tokens_out / 60, tokens_out / 25)} "
                "per analysis, a lot slower if Ollama or LM Studio runs on the CPU.")
    time_part = f"Usually {_duration(tokens_out / 200, tokens_out / 80)} per analysis"
    price = core.price_for(provider, model, prices)
    if not price:
        return (f"{time_part}. No price data for this model yet, so no cost estimate. "
                "Click Load models or check the provider's price page.")
    cost = core.format_usd(*core.cost_range(tokens_in, tokens_out, price, model))
    note = " Reasoning models also bill their hidden thinking, hence the wide range." if core.is_reasoning(model) else ""
    return f"{time_part}, costs {cost} (USD, estimate).{note}"


def preset_costs(provider, model, prices):
    """One line comparing all presets for the chosen model, or '' if there's nothing to compare."""
    price = core.price_for(provider, model, prices)
    if not price or core.PROVIDERS[provider]["where"] == "local":
        return ""
    parts = []
    for p in PRESETS.values():
        cost = core.format_usd(*core.cost_range(*core.analysis_tokens(p["top"], p["double_check"]), price, model))
        parts.append(f"{p['name']} {cost}")
    src = "OpenRouter's public price list" if price[2] == "OpenRouter" else "RAMCheck's built-in price"
    return f"With {model}: " + ", ".join(parts) + f" per analysis. Prices from {src}."


# ----------------------------------------------------------------- app ---

class App:
    def __init__(self, root):
        self.root = root
        self.cfg = core.load_config()
        self.q = queue.Queue()
        self.stop = threading.Event()
        self.refresh_now = threading.Event()

        self.procs, self.mem = [], None
        self.verdicts, self.summary, self.model, self.analyzed_at = {}, "", "", None
        self.analyzed_keys = set()
        self.history = collections.deque(maxlen=120)
        self.selected = None
        self.hover_key = None
        self.cell_owner = []
        self.iid_to_key = {}
        self.sort_col, self.sort_desc = "mem", True
        self.view = "all"
        self.hide_system = False
        self.busy = False
        self.minimized = False
        self.startup_entries, self.startup_by_key, self.entry_to_key = [], {}, {}
        self.startup_scanned = False
        self.analysis_note = ""
        self.progress_text = ""
        self.cleanup_dialog = None
        self.chats, self.chat_pending = {}, {}
        self.mem_hist = {}          # program key -> deque of (time, bytes), for spotting leaks
        self.growing = {}           # program key -> growth info
        self.test = None            # running memtest.MemTest
        self.hw = None              # RAM module info once loaded
        self.prices = {}

        self._fonts()
        self._styles()
        self._build()
        self.show_page("processes")

        last = core.load_last_analysis()
        if last:
            self.summary, self.verdicts, self.model = last["summary"], last["verdicts"], last["model"]
            self.analysis_note, self.analyzed_keys = last["note"], set(last["keys"])
            self.analyzed_at = dt.datetime.fromtimestamp(last["time"])
            self.btn_analyze.configure(text="Analyze again")
        if core.PROVIDERS[self.cfg["provider"]]["where"] == "cloud":
            self.load_prices()
        if not self.cfg.get("welcomed"):
            self.root.after(700, self.show_welcome)
        threading.Thread(target=self._measure_loop, daemon=True).start()
        self._poll()
        self._tick_live()
        root.protocol("WM_DELETE_WINDOW", self.close)
        # one mouse-wheel handler for the whole app: scrolls whatever is under the pointer
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            root.bind_all(seq, self._wheel, add="+")
        root.bind_all("<Tab>", lambda e: KEYBOARD.update(on=True), add="+")
        root.bind_all("<ButtonPress>", lambda e: KEYBOARD.update(on=False), add="+")
        root.bind("<F5>", lambda e: self.refresh())
        root.bind("<Control-Return>", lambda e: self.analyze())
        root.bind("<Control-f>", lambda e: self._focus_search())
        for i, key in enumerate(("processes", "memory", "startup", "setup", "settings"), start=1):
            root.bind(f"<Control-Key-{i}>", lambda e, k=key: self.show_page(k))
        root.report_callback_exception = self._on_error
        threading.excepthook = lambda a: core.log_error("".join(
            __import__("traceback").format_exception(a.exc_type, a.exc_value, a.exc_traceback)))
        self._restore_window()
        if self.cfg.get("check_updates", True) and core.install_mode() != "store":
            threading.Thread(target=lambda: self.q.put(("update", core.check_for_update())), daemon=True).start()
        root.bind("<Escape>", lambda e: self.clear_selection() if self.cleanup_dialog is None else None)
        root.bind("<Control-r>", lambda e: self.refresh())

    def _on_error(self, exc, val, tb):
        """Unexpected errors: log them, tell the user once, keep running."""
        import traceback
        core.log_error("".join(traceback.format_exception(exc, val, tb)))
        if getattr(self, "_error_shown", False):
            return
        self._error_shown = True
        if messagebox.askyesno("Something went wrong",
                               f"RAMCheck ran into an unexpected error ({exc.__name__}). It keeps running, "
                               f"but something may not have worked.\n\nDetails are saved in:\n{core.LOG_PATH}\n\n"
                               "Open the GitHub page to report it?", parent=self.root):
            webbrowser.open(core.REPO_URL + "/issues")

    def _focus_search(self):
        self.show_page("processes")
        self.search.focus_set()
        self.search.select_range(0, "end")

    def _restore_window(self):
        win = self.cfg.get("window") or {}
        m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", win.get("geometry", ""))
        if m:
            w, h, x, y = map(int, m.groups())
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            if w <= sw and h <= sh and -50 < x < sw - 100 and -10 < y < sh - 100:  # still on screen
                self.root.geometry(f"{w}x{h}+{x}+{y}")
        if win.get("zoomed") and os.name == "nt":
            self.root.state("zoomed")

    def _wheel(self, e):
        up = getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0
        w = self.root.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            handler = getattr(w, "_on_wheel", None)
            if handler:
                handler(up)
                return "break"
            w = getattr(w, "master", None)

    # ------------------------------------------------------------ setup ---

    def _fonts(self):
        disp = pick_family(self.root, "Bahnschrift SemiBold", "Bahnschrift",
                           "DejaVu Sans Condensed", "Segoe UI")
        body = pick_family(self.root, "Segoe UI", "DejaVu Sans")
        heavy = "normal" if "semibold" in disp.lower() else "bold"
        self.f = {
            "headline": (disp, 22, heavy),
            "title": (disp, 16, heavy),
            "brand": (disp, 14, heavy),
            "tab": (body, 10),
            "body": (body, 10),
            "small": (body, 9),
            "button": (body, 10),
            "strong": (body, 10, "bold"),
            "editor": (pick_family(self.root, "Cascadia Mono", "Consolas", "DejaVu Sans Mono"), 10),
        }

    def _styles(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                     bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL, borderwidth=0,
                     rowheight=S(30), font=self.f["body"])
        st.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
        st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.configure("Treeview.Heading", background=PANEL, foreground=MUTED, relief="flat",
                     font=self.f["small"], bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL,
                     padding=(S(3), S(8)))  # small side padding so headings line up with the cell text
        st.map("Treeview.Heading", background=[("active", RAISED)], foreground=[("active", TEXT)])
        for orient in ("Vertical", "Horizontal"):  # slim bars without arrow buttons
            st.layout(f"{orient}.TScrollbar", [(f"{orient}.Scrollbar.trough", {"sticky": "nswe", "children": [
                (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
            st.configure(f"{orient}.TScrollbar", background=LINE, troughcolor=PANEL, bordercolor=PANEL,
                         lightcolor=LINE, darkcolor=LINE, gripcount=0, arrowsize=S(8), relief="flat")
            st.map(f"{orient}.TScrollbar", background=[("active", DIM), ("pressed", MUTED)],
                   lightcolor=[("active", DIM)], darkcolor=[("active", DIM)])
        st.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=TEXT,
                     arrowcolor=MUTED, bordercolor=LINE, lightcolor=PANEL, darkcolor=PANEL,
                     insertcolor=CYAN, selectbackground=PANEL, selectforeground=TEXT,
                     padding=S(4))
        st.map("TCombobox", fieldbackground=[("readonly", PANEL)], bordercolor=[("focus", CYAN), ("hover", DIM)],
               selectbackground=[("focus", PANEL), ("!focus", PANEL)],
               selectforeground=[("focus", TEXT), ("!focus", TEXT)],
               background=[("active", RAISED), ("pressed", RAISED)], arrowcolor=[("active", TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
        self.root.option_add("*TCombobox*Listbox.font", self.f["body"])

    def _build(self):
        r = self.root
        r.configure(bg=VOID)

        # header
        head = tk.Frame(r, bg=VOID)
        head.pack(fill="x", padx=S(20), pady=(S(10), 0))
        logo = tk.Canvas(head, width=S(22), height=S(22), bg=VOID, highlightthickness=0)
        self._draw_logo(logo)
        logo.pack(side="left", padx=(0, S(8)))
        tk.Label(head, text="RAMCheck", bg=VOID, fg=TEXT, font=self.f["brand"]).pack(side="left")
        self.tabbar = TabBar(head, (("processes", "Programs"), ("memory", "Memory"), ("startup", "Startup"),
                                    ("setup", "My setup"), ("settings", "Settings")), self.show_page, self.f["tab"])
        self.tabbar.pack(side="left", padx=(S(28), 0))

        self.btn_analyze = FlatButton(head, "Analyze with AI", self.analyze, "primary",
                                      self.f["strong"], padx=16)
        self.btn_analyze.pack(side="right")
        self.btn_analyze.set_enabled(False)
        self.cleanup_btn = FlatButton(head, "Clean up", self.open_cleanup, "alert", self.f["strong"], padx=14)
        self.cleanup_btn.pack(side="right", padx=(0, S(8)))
        self.cleanup_btn.set_enabled(False)
        self.btn_refresh = FlatButton(head, "Refresh", self.refresh, "ghost", self.f["button"])
        self.btn_refresh.pack(side="right", padx=S(8))
        if os.name == "nt" and not core.is_admin():
            admin_btn = FlatButton(head, "Run as admin", self.run_as_admin, "quiet", self.f["button"])
            admin_btn.pack(side="right")
            Tooltip(admin_btn, "Restarts RAMCheck with admin rights, needed to stop services and to see "
                               "protected processes. Your analysis is kept.", self.f["small"])
        Tooltip(self.btn_refresh, "Measure again now (F5)", self.f["small"])
        Tooltip(self.btn_analyze, "Let the AI assess the biggest programs (Ctrl+Enter)", self.f["small"])
        Tooltip(self.cleanup_btn, "Close what's marked as bloatware or optional and stop it from starting "
                                  "with Windows. You pick what, nothing happens without confirming.", self.f["small"])

        # separator line that turns into a moving progress bar while RAMCheck is working
        self.loader = tk.Canvas(r, height=S(2), bg=VOID, highlightthickness=0)
        self.loader.pack(fill="x")
        self.loader_base = self.loader.create_rectangle(0, 0, 4000, 1, fill=LINE, width=0)
        self.loader_bar = self.loader.create_rectangle(0, 0, 0, S(2), fill=CYAN, width=0)
        self._loading = 0

        # status bar (packed before the pages so it stays visible when the window shrinks)
        bar = tk.Frame(r, bg=VOID)
        bar.pack(side="bottom", fill="x", padx=S(20), pady=S(8))
        self.status = tk.Label(bar, text="Measuring your programs ...", bg=VOID, fg=MUTED,
                               font=self.f["small"], anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        self.savings_lbl = tk.Label(bar, text="", bg=VOID, fg=MUTED, font=self.f["small"])
        self.savings_lbl.pack(side="right")
        self.update_lbl = tk.Label(bar, text="", bg=VOID, fg=CYAN, font=self.f["small"] + ("underline",),
                                   cursor="hand2")
        self.update_lbl.pack(side="right", padx=(0, S(18)))

        pages = tk.Frame(r, bg=VOID)
        pages.pack(fill="both", expand=True)
        pages.rowconfigure(0, weight=1)
        pages.columnconfigure(0, weight=1)
        self.pages = {
            "processes": self._build_processes(pages),
            "memory": self._build_memory(pages),
            "startup": self._build_startup(pages),
            "setup": self._build_setup(pages),
            "settings": self._build_settings(pages),
        }
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")

    def _draw_logo(self, c):
        s = S(22)
        cell = (s - S(4)) / 3
        colors = [CYAN, CYAN, MAGENTA, CYAN, "#1fb3c4", DIM, "#1fb3c4", DIM, DIM]
        for i, col in enumerate(colors):
            x, y = (i % 3) * (cell + S(2)), (i // 3) * (cell + S(2))
            c.create_rectangle(x, y, x + cell, y + cell, fill=col, width=0)

    # ------------------------------------------------------ programs page ---

    def _build_processes(self, parent):
        page = tk.Frame(parent, bg=VOID)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)

        top = tk.Frame(page, bg=VOID)
        top.grid(row=0, column=0, sticky="ew", padx=S(20), pady=(S(16), S(10)))
        top.columnconfigure(0, weight=1)
        self.headline = tk.Label(top, text="Reading memory ...", bg=VOID, fg=TEXT,
                                 font=self.f["headline"], anchor="w")
        self.headline.grid(row=0, column=0, sticky="sw")
        self.subline = tk.Label(top, text="", bg=VOID, fg=MUTED, font=self.f["body"], anchor="w")
        self.subline.grid(row=1, column=0, sticky="nw", pady=(S(2), 0))

        graph_box = tk.Frame(top, bg=VOID)
        graph_box.grid(row=0, column=1, rowspan=2, sticky="e")
        self.graph = tk.Canvas(graph_box, width=S(260), height=S(46), bg=VOID, highlightthickness=0)
        self.graph.pack()
        tk.Label(graph_box, text="Memory use, last 2 minutes", bg=VOID, fg=DIM,
                 font=self.f["small"]).pack(anchor="e")

        self.map = tk.Canvas(top, height=S(8 * 16), bg=VOID, highlightthickness=0)
        self.map.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(S(14), S(6)))
        self.map.bind("<Configure>", lambda e: self.draw_map())
        self.map.bind("<Motion>", self._map_motion)
        self.map.bind("<Leave>", lambda e: self._set_hover(None))
        self.map.bind("<Button-1>", self._map_click)

        under = tk.Frame(top, bg=VOID)
        under.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.legend = tk.Frame(under, bg=VOID)
        self.legend.pack(side="left")
        self.hover_lbl = tk.Label(under, text="", bg=VOID, fg=TEXT, font=self.f["body"])
        self.hover_lbl.pack(side="right")

        body = tk.Frame(page, bg=VOID)
        body.grid(row=1, column=0, sticky="nsew", padx=S(20), pady=(S(6), 0))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        # filter row
        filt = tk.Frame(body, bg=VOID)
        filt.grid(row=0, column=0, sticky="ew", pady=(0, S(8)))
        self.search = styled_entry(filt, self.f["body"], width=22)
        self.search.pack(side="left", ipady=S(5))
        self._placeholder(self.search, "Filter by name")
        self.search.bind("<KeyRelease>", lambda e: self.refresh_table())
        self.view_seg = Segmented(filt, (("all", "All"), ("look", "Worth a look")), self.set_view, self.f["button"])
        self.view_seg.pack(side="left", padx=(S(10), 0))
        hide = tk.Frame(filt, bg=VOID)
        hide.pack(side="left", padx=(S(18), 0))
        self.hide_switch = Switch(hide, False, lambda on: self.toggle_hide_system(on))
        self.hide_switch.pack(side="left")
        hide_lbl = self.hide_lbl = tk.Label(hide, text="Hide Windows system", bg=VOID, fg=MUTED,
                                            font=self.f["button"], cursor="hand2")
        hide_lbl.pack(side="left", padx=(S(8), 0))
        hide_lbl.bind("<Button-1>", lambda e: self.hide_switch.toggle())
        self.view = "all"

        # table
        table = tk.Frame(body, bg=PANEL)
        table.grid(row=1, column=0, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        cols = ("name", "mem", "count", "auto", "verdict")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", selectmode="browse")
        self.headings = {"name": "Program", "mem": "RAM", "count": "Processes", "auto": "Autostart",
                         "verdict": "Verdict"}
        for c, w, anchor, stretch in (("name", 260, "w", True), ("mem", 110, "e", False),
                                      ("count", 90, "center", False), ("auto", 90, "center", False),
                                      ("verdict", 140, "w", False)):
            self.tree.heading(c, text=self.headings[c], anchor=anchor,
                              command=lambda col=c: self.sort_by(col))
            self.tree.column(c, width=S(w), anchor=anchor, stretch=stretch, minwidth=S(60))
        for cat, color in ROW_COLORS.items():
            self.tree.tag_configure(cat, foreground=color)
        sb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(S(8), 0), pady=(S(4), S(6)))
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        hover_rows(self.tree)
        self.tree.bind("<Button-3>", self._program_menu)
        self._update_headings()

        # detail panel
        self.detail = tk.Frame(body, bg=PANEL, width=S(350))
        self.detail.grid(row=0, column=1, rowspan=2, sticky="ns", padx=(S(14), 0))
        self.detail.pack_propagate(False)
        self.render_detail()
        return page

    def _placeholder(self, entry, text):
        def show(_e=None):
            if not entry.get():
                entry.insert(0, text)
                entry.configure(fg=DIM)
                entry.is_placeholder = True

        def hide(_e=None):
            if getattr(entry, "is_placeholder", False):
                entry.delete(0, "end")
                entry.configure(fg=TEXT)
                entry.is_placeholder = False

        entry.bind("<FocusIn>", hide, add="+")
        entry.bind("<FocusOut>", show, add="+")
        show()

    def _search_text(self):
        if getattr(self.search, "is_placeholder", False):
            return ""
        return self.search.get().strip().lower()

    # -------------------------------------------------------- memory page ---

    def _build_memory(self, parent):
        page = tk.Frame(parent, bg=VOID)
        outer, inner = scrollable(page, VOID, self.root)
        outer.pack(fill="both", expand=True)
        inner.configure(padx=S(20), pady=S(18))
        f = self.f
        wrap = S(820)

        def title(text, top=S(26)):
            tk.Label(inner, text=text, bg=VOID, fg=TEXT, font=f["title"]).pack(anchor="w", pady=(top, S(4)))

        def para(text, fg=MUTED, parent=None):
            lbl = tk.Label(parent or inner, text=text, bg=VOID, fg=fg, font=f["body"], justify="left",
                           wraplength=wrap, anchor="w")
            lbl.pack(anchor="w", fill="x")
            return lbl

        # your RAM
        title("Your RAM", 0)
        self.hw_summary = tk.Label(inner, text="Reading module info ...", bg=VOID, fg=TEXT, font=f["headline"],
                                   anchor="w")
        self.hw_summary.pack(anchor="w", pady=(S(2), S(8)))
        self.hw_table = tk.Frame(inner, bg=PANEL)  # shown once module info has arrived
        self.hw_hints = tk.Frame(inner, bg=VOID)
        self.hw_hints.pack(anchor="w", fill="x", pady=(S(10), 0))

        # where it goes
        title("Where your memory goes")
        tiles = tk.Frame(inner, bg=VOID)
        tiles.pack(anchor="w", fill="x", pady=(S(4), 0))
        self.tiles = {}
        for i, (key, label, tip) in enumerate((
                ("used", "In use", "Memory programs and Windows are using right now."),
                ("commit", "Committed", "Memory programs have reserved, including the part that's in the page file."),
                ("pagefile", "Page file", "Memory Windows moved to the SSD because RAM was needed elsewhere."),
                ("kernel", "Windows kernel", "Memory the Windows core and drivers use."),
                ("reserved", "Hardware reserved", "Taken by the hardware before Windows starts, "
                                                   "for example by integrated graphics."))):
            box = tk.Frame(tiles, bg=PANEL, padx=S(14), pady=S(10))
            box.grid(row=0, column=i, sticky="nsew", padx=(0, S(8)))
            tiles.columnconfigure(i, weight=1, uniform="t")
            tk.Label(box, text=label, bg=PANEL, fg=MUTED, font=f["small"]).pack(anchor="w")
            val = tk.Label(box, text="...", bg=PANEL, fg=TEXT, font=f["title"])
            val.pack(anchor="w", pady=(S(2), 0))
            sub = tk.Label(box, text="", bg=PANEL, fg=DIM, font=f["small"])
            sub.pack(anchor="w")
            self.tiles[key] = (val, sub)
            Tooltip(box, tip, f["small"])

        # RAM test inside Windows
        title("Test your RAM for errors")
        para("RAMCheck fills free memory with known patterns, reads everything back and reports every byte that "
             "comes back wrong. Errors mean faulty RAM or unstable XMP/EXPO or overclocking settings. It can only "
             "test memory Windows isn't using, so a clean result is a good sign, not a guarantee. For the full "
             "check, use the test outside Windows below.")
        row = tk.Frame(inner, bg=VOID)
        row.pack(anchor="w", fill="x", pady=(S(12), 0))
        self.test_seg = Segmented(row, [(k, p["name"]) for k, p in memtest.PRESETS.items()],
                                  lambda k: self._update_test_plan(), f["button"], value="quick")
        self.test_seg.pack(side="left")
        self.test_btn = FlatButton(row, "Start test", self.toggle_test, "primary", f["strong"], padx=16)
        self.test_btn.pack(side="left", padx=(S(14), 0))
        self.test_plan = tk.Label(inner, text="", bg=VOID, fg=MUTED, font=f["small"], justify="left",
                                  wraplength=wrap, anchor="w")
        self.test_plan.pack(anchor="w", fill="x", pady=(S(8), 0))
        self.test_canvas = tk.Canvas(inner, height=S(92), bg=VOID, highlightthickness=0)
        self.test_canvas.pack(anchor="w", fill="x", pady=(S(12), S(6)))
        self.test_canvas.bind("<Configure>", lambda e: self._draw_test())
        self.test_status = tk.Label(inner, text="", bg=VOID, fg=MUTED, font=f["body"], anchor="w")
        self.test_status.pack(anchor="w", fill="x")
        self.test_result = tk.Frame(inner, bg=VOID)
        self.test_result.pack(anchor="w", fill="x", pady=(S(8), 0))

        # outside Windows
        title("Full test outside Windows")
        para("Windows has its own memory test that runs before Windows starts, so it can check all of your RAM. "
             "It needs a restart and takes about 15 to 30 minutes, the result appears here afterwards.")
        row2 = tk.Frame(inner, bg=VOID)
        row2.pack(anchor="w", pady=(S(10), 0))
        FlatButton(row2, "Schedule Windows Memory Diagnostic", self._schedule_windows_test, "ghost",
                   f["button"]).pack(side="left")
        link = tk.Label(row2, text="Even more thorough: MemTest86 from a USB stick", bg=VOID, fg=CYAN,
                        font=f["small"] + ("underline",), cursor="hand2")
        link.pack(side="left", padx=(S(16), 0))
        link.bind("<Button-1>", lambda e: webbrowser.open("https://www.memtest86.com/"))
        self.win_test = tk.Label(inner, text="", bg=VOID, fg=MUTED, font=f["small"], anchor="w")
        self.win_test.pack(anchor="w", pady=(S(8), 0))

        # growing programs
        title("Programs that keep growing")
        para("While RAMCheck is open, it watches whether a program's memory keeps climbing. That can be a "
             "memory leak, restarting the program usually fixes it. Browsers grow when you open tabs, that's "
             "normal.")
        self.grow_box = tk.Frame(inner, bg=VOID)
        self.grow_box.pack(anchor="w", fill="x", pady=(S(8), S(12)))
        self._update_test_plan()
        self._render_growth()
        return page

    def _load_hardware(self):
        mods = hardware.modules()
        slots = hardware.slot_count() if mods else None
        self.q.put(("hw", {"modules": mods, "slots": slots, "hints": hardware.hints(mods, slots),
                           "last_test": hardware.last_windows_test()}))

    def _render_hw(self):
        hw, f = self.hw or {}, self.f
        mods = hw.get("modules") or []
        for w in self.hw_table.winfo_children() + self.hw_hints.winfo_children():
            w.destroy()
        if not mods:
            self.hw_summary.configure(text="Module details aren't available" if os.name == "nt"
                                      else "Module details are only available on Windows")
            self.hw_table.pack_forget()
        else:
            total = sum(m["size"] for m in mods)
            kind = next((m["type"] for m in mods if m["type"]), "")
            speed = max((m["speed"] for m in mods), default=0)
            self.hw_summary.configure(text=f"{total / core.GB:.0f} GB {kind}, {len(mods)} module"
                                           f"{'s' if len(mods) != 1 else ''}" + (f", {speed} MT/s" if speed else ""))
            self.hw_table.pack(anchor="w", fill="x", before=self.hw_hints)
            heads = ("Slot", "Size", "Type", "Speed", "Maker", "Part number")
            for c, h in enumerate(heads):
                tk.Label(self.hw_table, text=h, bg=PANEL, fg=DIM, font=f["small"], anchor="w").grid(
                    row=0, column=c, sticky="w", padx=(S(14), S(10)), pady=(S(8), S(2)))
            for r, m in enumerate(mods, start=1):
                vals = (m["slot"], f"{m['size'] / core.GB:.0f} GB", m["type"] or "?",
                        f"{m['speed']} MT/s" if m["speed"] else "?", m["maker"] or "?", m["part"] or "?")
                for c, v in enumerate(vals):
                    tk.Label(self.hw_table, text=v, bg=PANEL, fg=TEXT, font=f["body"], anchor="w").grid(
                        row=r, column=c, sticky="w", padx=(S(14), S(10)), pady=(0, S(8) if r == len(mods) else S(2)))
        for level, text in hw.get("hints") or []:
            line = tk.Frame(self.hw_hints, bg=VOID)
            line.pack(anchor="w", fill="x", pady=(0, S(4)))
            mark = tk.Canvas(line, width=S(8), height=S(8), bg=VOID, highlightthickness=0)
            mark.create_rectangle(0, 0, S(8), S(8), fill="#ffc857" if level == "warn" else MINT_DIM, width=0)
            mark.pack(side="left", anchor="n", pady=(S(6), 0))
            tk.Label(line, text=text, bg=VOID, fg=TEXT if level == "warn" else MUTED, font=f["body"],
                     justify="left", wraplength=S(800), anchor="w").pack(side="left", padx=(S(10), 0))
        last = hw.get("last_test")
        if last:
            self.win_test.configure(text=f"Last Windows Memory Diagnostic: {last['date']}, " +
                                         ("no errors found." if last["ok"] else "it found errors!"),
                                    fg=MUTED if last["ok"] else MAGENTA)
        else:
            self.win_test.configure(text="Windows Memory Diagnostic hasn't run on this PC yet (or its result "
                                         "was cleared from the event log).", fg=DIM)
        self._update_tiles(core.memory_status())

    def _update_tiles(self, mem):
        if not hasattr(self, "tiles"):
            return
        info = hardware.performance_info()
        gb = lambda b: f"{b / core.GB:.1f} GB"
        self.tiles["used"][0].configure(text=gb(mem["used"]))
        self.tiles["used"][1].configure(text=f"of {gb(mem['total'])}")
        if info:
            self.tiles["commit"][0].configure(text=gb(info["commit"]))
            self.tiles["commit"][1].configure(text=f"limit {gb(info['commit_limit'])}")
            self.tiles["kernel"][0].configure(text=gb(info["kernel_paged"] + info["kernel_nonpaged"]))
            self.tiles["kernel"][1].configure(text=f"{info['processes']} processes")
        else:
            for k in ("commit", "kernel"):
                self.tiles[k][0].configure(text="n/a")
        try:
            import psutil
            sw = psutil.swap_memory()
            self.tiles["pagefile"][0].configure(text=gb(sw.used))
            self.tiles["pagefile"][1].configure(text=f"of {gb(sw.total)}" if sw.total else "no page file")
        except Exception:
            self.tiles["pagefile"][0].configure(text="n/a")
        installed = sum(m["size"] for m in (self.hw or {}).get("modules") or [])
        if installed:
            self.tiles["reserved"][0].configure(text=gb(max(0, installed - mem["total"])))
            self.tiles["reserved"][1].configure(text=f"of {gb(installed)} installed")
        else:
            self.tiles["reserved"][0].configure(text="n/a")

    # RAM test
    def _update_test_plan(self):
        if self.test:
            return
        preset = self.test_seg.get()
        p = memtest.plan(core.memory_status()["available"], preset)
        if p["total"] < 256 * memtest.MB:
            self.test_plan.configure(text="Not enough free memory for a meaningful test right now. Close some "
                                          "programs and try again.", fg="#ffc857")
            self.test_btn.set_enabled(False)
            return
        self.test_btn.set_enabled(True)
        steps = len(memtest.PATTERNS) * 2 * p["passes"]
        work = p["total"] * steps
        lo, hi = work / (12 * memtest.GB), work / (3 * memtest.GB)
        wait = 60 if p["fade"] else 0
        self.test_plan.configure(
            text=f"{memtest.PRESETS[preset]['desc']} Tests {p['total'] / core.GB:.1f} GB with {p['threads']} "
                 f"thread{'s' if p['threads'] != 1 else ''}, roughly {_duration(lo + wait, hi + wait)}. "
                 "Save your work first, the PC will be slower while it runs.", fg=MUTED)
        self._planned = p

    def toggle_test(self):
        if self.test and not self.test.status()["finished"]:
            self.test.stop()
            self.test_btn.configure(text="Stopping ...")
            self.test_btn.set_enabled(False)
            return
        self._update_test_plan()
        p = getattr(self, "_planned", None)
        if not p or not messagebox.askyesno(
                "Test your RAM",
                f"RAMCheck will use {p['total'] / core.GB:.1f} GB of your free memory for the test. Other programs "
                "will be slower until it's done, and games shouldn't run at the same time.\n\nStart now?",
                parent=self.root):
            return
        self.test = memtest.MemTest(p["per_thread"], p["threads"], p["passes"], p["fade"])
        self.test.start()
        self.test_btn.configure(text="Stop test")
        self.test_btn.bg_normal, self.test_btn.fg_normal = PANEL, MAGENTA
        self.test_btn._paint()
        for w in self.test_result.winfo_children():
            w.destroy()
        self.start_loading()
        self._poll_test()

    def _poll_test(self):
        if not self.test:
            return
        st = self.test.status()
        self._draw_test(st)
        if st["failed"]:
            text, color = st["failed"], "#ffc857"
        elif st["finished"]:
            text, color = "", MUTED
        else:
            left = f", about {_duration(st['remaining'], st['remaining'] * 1.3)} left" if st["remaining"] > 3 else ""
            errs = f"{st['errors']} error{'s' if st['errors'] != 1 else ''}"
            text = (f"{st['phase']}: pass {st['pass']} of {st['passes']}, {st['pattern']}. "
                    f"{st['progress'] * 100:.0f} %, {st['speed'] / core.GB:.1f} GB/s{left}. {errs}.")
            color = MAGENTA if st["errors"] else MUTED
        self.test_status.configure(text=text, fg=color)
        if st["finished"]:
            self._test_done(st)
        else:
            self.root.after(250, self._poll_test)

    def _test_done(self, st):
        self.stop_loading()
        self.test_btn.configure(text="Start test")
        self.test_btn.bg_normal, self.test_btn.fg_normal = CYAN, VOID
        self.test_btn.set_enabled(True)
        box, f = self.test_result, self.f
        for w in box.winfo_children():
            w.destroy()
        if st["failed"]:
            self.test = None
            self._update_test_plan()
            return
        size = f"{st['total_bytes'] / core.GB:.1f} GB"
        if st["errors"]:
            head, color = f"{st['errors']} error{'s' if st['errors'] != 1 else ''} found in {size}.", MAGENTA
            advice = ("Memory returned data that differs from what was written. That's never normal. If XMP or EXPO "
                      "is on, switch it off in the BIOS and test again: if the errors disappear, the profile isn't "
                      "stable on your system. If they stay, test one module at a time or run MemTest86 to find "
                      "the faulty one.")
        elif st["stopped"]:
            head, color = f"Stopped after {st['progress'] * 100:.0f} %, no errors up to that point.", MUTED
            advice = "Run the full test for a real answer."
        else:
            head, color = f"No errors found in {size} after {st['passes']} pass{'es' if st['passes'] != 1 else ''}.", MINT
            advice = ("The part of your RAM that could be tested works correctly. Memory Windows was using at the "
                      "time wasn't included, the test outside Windows covers that.")
        card = tk.Frame(box, bg=PANEL)
        card.pack(anchor="w", fill="x")
        bar = tk.Frame(card, bg=color, width=S(3))
        bar.pack(side="left", fill="y")
        body = tk.Frame(card, bg=PANEL)
        body.pack(side="left", fill="x", expand=True, padx=S(14), pady=S(10))
        tk.Label(body, text=head, bg=PANEL, fg=color, font=f["strong"], anchor="w").pack(anchor="w")
        tk.Label(body, text=advice, bg=PANEL, fg=MUTED, font=f["body"], justify="left", wraplength=S(780),
                 anchor="w").pack(anchor="w", pady=(S(4), 0))
        for e in st["error_list"][:6]:
            bits = ", ".join(str(b) for b in range(8) if e["flipped"] >> b & 1)
            tk.Label(body, text=f"{e['pattern']} (pass {e['pass']}): at offset {e['offset'] / core.MB:,.1f} MB of "
                                f"thread {e['thread'] + 1}, expected 0x{e['expected']:02X}, got 0x{e['found']:02X} "
                                f"(bit {bits} flipped)", bg=PANEL, fg=DIM, font=f["small"], anchor="w").pack(anchor="w")
        self.test = None
        self._update_test_plan()

    def _draw_test(self, st=None):
        """One lane of cells per thread; cells light up as that thread's work gets done."""
        c = self.test_canvas
        c.delete("all")
        W = c.winfo_width()
        if W < 50:
            return
        lanes = (st and len(st["per_thread"])) or getattr(self, "_planned", {}).get("threads", 4)
        cols, gap = 64, max(1, S(2))
        lane_h = S(14)
        want = lanes * lane_h + gap * (lanes - 1)
        if int(c.cget("height")) != want:
            c.configure(height=want)
        cw = (W - gap * (cols - 1)) / cols
        errors_at = {}
        if st:
            per_thread_bytes = st["total_bytes"] / max(1, lanes)
            for e in st["error_list"]:
                errors_at[(e["thread"], int(e["offset"] / per_thread_bytes * cols))] = True
        for lane in range(lanes):
            frac = st["per_thread"][lane] if st else 0
            lit = frac * cols
            for col in range(cols):
                x, y = col * (cw + gap), lane * (lane_h + gap)
                if (lane, col) in errors_at:
                    color = MAGENTA
                elif col < int(lit):
                    color = "#1fb3c4" if (col + lane) % 2 else CYAN
                elif col == int(lit) and st and not st["finished"]:
                    color = mix(PANEL, CYAN, lit - int(lit))
                else:
                    color = PANEL
                c.create_rectangle(x, y, x + cw, y + lane_h, fill=color, width=0)

    def _schedule_windows_test(self):
        if hardware.schedule_windows_test():
            self.set_status("Windows Memory Diagnostic opened. Choose whether to restart now or next time.")
        else:
            self.set_status("Couldn't open Windows Memory Diagnostic. Press Win+R and run mdsched.exe.", "#ffc857")

    # leaks
    def _track_growth(self):
        now = time.time()
        seen = set()
        for g in self.procs:
            key = g["key"]
            seen.add(key)
            hist = self.mem_hist.setdefault(key, collections.deque(maxlen=720))
            hist.append((now, g["mem"]))
        for key in list(self.mem_hist):
            if key not in seen:
                del self.mem_hist[key]
                self.growing.pop(key, None)
        growing = {}
        for key, hist in self.mem_hist.items():
            if len(hist) < 6 or hist[-1][0] - hist[0][0] < 600:  # need at least 10 minutes of history
                continue
            start = sum(m for _, m in list(hist)[:3]) / 3
            end = sum(m for _, m in list(hist)[-3:]) / 3
            peak = max(m for _, m in hist)
            grew = end - start
            if grew >= 300 * core.MB and grew >= 0.3 * start and end >= 0.9 * peak:
                minutes = (hist[-1][0] - hist[0][0]) / 60
                growing[key] = {"from": start, "to": end, "minutes": minutes, "rate": grew / minutes}
        self.growing = growing
        if hasattr(self, "grow_box"):
            self._render_growth()

    def _render_growth(self):
        box = self.grow_box
        for w in box.winfo_children():
            w.destroy()
        if not self.growing:
            watched = max((h[-1][0] - h[0][0] for h in self.mem_hist.values()), default=0) / 60
            text = ("Nothing suspicious so far." if watched >= 10 else
                    "Watching. Results show up after about 10 minutes.")
            tk.Label(box, text=text, bg=VOID, fg=DIM, font=self.f["small"]).pack(anchor="w")
            return
        for key, info in sorted(self.growing.items(), key=lambda kv: -kv[1]["rate"]):
            g = self._group(key)
            name = g["name"] if g else key
            tk.Label(box, text=f"{name}: {info['from'] / core.GB:.1f} to {info['to'] / core.GB:.1f} GB in "
                               f"{info['minutes']:.0f} minutes (+{info['rate'] / core.MB:.0f} MB per minute)",
                     bg=VOID, fg="#ffc857", font=self.f["body"], anchor="w").pack(anchor="w", pady=(0, S(3)))

    # ------------------------------------------------------- startup page ---

    def _build_startup(self, parent):
        page = tk.Frame(parent, bg=VOID)
        inner = tk.Frame(page, bg=VOID)
        inner.pack(fill="both", expand=True, padx=S(20), pady=S(18))
        tk.Label(inner, text="Startup", bg=VOID, fg=TEXT, font=self.f["title"]).pack(anchor="w")
        tk.Label(inner, bg=VOID, fg=MUTED, font=self.f["body"], justify="left", wraplength=S(760),
                 text="Everything RAMCheck found that starts with Windows. Turning a startup app off works "
                      "like in Task Manager and can be undone here any time. Services are set to manual, so "
                      "they still start when a program really asks for them. Changing services needs admin "
                      "rights.").pack(anchor="w", pady=(S(4), S(12)))
        table = tk.Frame(inner, bg=PANEL)
        table.pack(fill="both", expand=True)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        cols = ("name", "kind", "state", "verdict", "command")
        self.stree = ttk.Treeview(table, columns=cols, show="headings", selectmode="extended")
        self.s_headings = {}
        self.s_sort_col, self.s_sort_desc = None, False
        for c, text, w, stretch in (("name", "Name", 220, False), ("kind", "Type", 190, False),
                                    ("state", "Starts", 150, False), ("verdict", "Verdict", 130, False),
                                    ("command", "Command", 300, True)):
            self.s_headings[c] = text
            self.stree.heading(c, text=text, anchor="w", command=lambda col=c: self._sort_startup(col))
            self.stree.column(c, width=S(w), anchor="w", stretch=stretch, minwidth=S(60))
        for cat, color in ROW_COLORS.items():
            self.stree.tag_configure(cat, foreground=color)
        self.stree.tag_configure("off", foreground=DIM)
        sb = ttk.Scrollbar(table, orient="vertical", command=self.stree.yview)
        self.stree.configure(yscrollcommand=sb.set)
        self.stree.grid(row=0, column=0, sticky="nsew", padx=(S(8), 0), pady=(S(4), S(6)))
        sb.grid(row=0, column=1, sticky="ns")
        self.stree.bind("<<TreeviewSelect>>", lambda e: self._startup_buttons())
        hover_rows(self.stree)
        self.stree.bind("<Button-3>", self._startup_menu)
        row = tk.Frame(inner, bg=VOID)
        row.pack(fill="x", pady=(S(12), 0))
        self.btn_s_off = FlatButton(row, "Turn off", lambda: self._startup_selected(False), "danger", self.f["button"])
        self.btn_s_off.pack(side="left")
        self.btn_s_on = FlatButton(row, "Turn on", lambda: self._startup_selected(True), "ghost", self.f["button"])
        self.btn_s_on.pack(side="left", padx=S(8))
        FlatButton(row, "Scan again", self.rescan_startup, "quiet", self.f["button"]).pack(side="left")
        FlatButton(row, "Windows startup settings", lambda: self.open_settings_uri("ms-settings:startupapps"),
                   "quiet", self.f["button"]).pack(side="right")
        self.startup_msg = tk.Label(inner, text="Scanning ...", bg=VOID, fg=MUTED, font=self.f["small"],
                                    anchor="w", justify="left", wraplength=S(760))
        self.startup_msg.pack(fill="x", pady=(S(8), 0))
        self._startup_buttons()
        return page

    def _sort_startup(self, col):
        if self.s_sort_col == col:
            self.s_sort_desc = not self.s_sort_desc
        else:
            self.s_sort_col, self.s_sort_desc = col, False
        for c, text in self.s_headings.items():
            arrow = (" ▾" if self.s_sort_desc else " ▴") if c == self.s_sort_col else ""
            self.stree.heading(c, text=text + arrow)
        self.refresh_startup_table()

    def _startup_sort_key(self):
        cats = list(core.CATEGORIES)
        kinds = {"service": 1, "run": 0, "folder": 0}

        def verdict(e):
            v = self.verdicts.get(self.entry_to_key.get(e["id"]))
            return cats.index(v["category"]) if v else len(cats)
        return {
            None: lambda e: (kinds[e["kind"]], e["name"].lower()),
            "name": lambda e: e["name"].lower(),
            "kind": lambda e: e["label"],
            "state": lambda e: not e["enabled"],
            "verdict": verdict,
            "command": lambda e: (e["command"] or "").lower(),
        }[self.s_sort_col]

    def refresh_startup_table(self):
        t = self.stree
        sel = set(t.selection())
        t.delete(*t.get_children())
        rows = sorted(self.startup_entries, key=lambda e: e["name"].lower())  # ties stay alphabetical
        rows = sorted(rows, key=self._startup_sort_key(), reverse=self.s_sort_desc)
        for e in rows:
            key = self.entry_to_key.get(e["id"])
            v = self.verdicts.get(key) if key else None
            if e["kind"] == "service":
                state = "Automatically" if e["enabled"] else "Manual"
            else:
                state = "On" if e["enabled"] else "Off"
            tags = ["off"] if not e["enabled"] else ([v["category"]] if v else [])
            t.insert("", "end", iid=e["id"], tags=tags,
                     values=(e["name"], e["label"], state, core.CATEGORIES[v["category"]] if v else "",
                             e["command"]))
        for iid in sel:
            if t.exists(iid):
                t.selection_add(iid)
        n_on = sum(e["enabled"] for e in self.startup_entries)
        if os.name != "nt":
            text = "Startup entries can only be read on Windows."
        else:
            text = (f"{len(self.startup_entries)} entries, {n_on} start with Windows. Scheduled tasks aren't "
                    "listed here, some updaters use those instead.")
            if not core.is_admin():
                text += " Run as admin to change services and entries for all users."
        note = getattr(self, "_startup_note", None)
        self._startup_note = None
        if note:
            text = f"{note[0]} {text}"
        self.startup_msg.configure(text=text, fg=MUTED if not note or note[1] else "#ffc857")
        self._startup_buttons()

    def _selected_entries(self):
        ids = set(self.stree.selection())
        return [e for e in self.startup_entries if e["id"] in ids]

    def _startup_buttons(self):
        sel = self._selected_entries()
        self.btn_s_off.set_enabled(any(e["enabled"] for e in sel))
        self.btn_s_on.set_enabled(any(not e["enabled"] for e in sel))

    def _startup_selected(self, enabled):
        todo = [e for e in self._selected_entries() if e["enabled"] != enabled]
        if todo:
            self.startup_msg.configure(text="Working ...", fg=MUTED)
            self._set_entries(todo, enabled)

    # -------------------------------------------------------- setup page ---

    def _build_setup(self, parent):
        page = tk.Frame(parent, bg=VOID)
        inner = tk.Frame(page, bg=VOID)
        inner.pack(fill="both", expand=True, padx=S(20), pady=S(18))
        tk.Label(inner, text="My setup", bg=VOID, fg=TEXT, font=self.f["title"]).pack(anchor="w")
        tk.Label(inner, bg=VOID, fg=MUTED, font=self.f["body"], justify="left", wraplength=S(720),
                 text="Tell the AI what you actually use, one fact per line. Anything you list as "
                      "used won't be flagged as unnecessary, and things you say you don't need can be. "
                      "Lines starting with # are ignored.").pack(anchor="w", pady=(S(4), S(12)))
        box = tk.Frame(inner, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="both", expand=True)
        self.setup_text = tk.Text(box, bg=PANEL, fg=TEXT, insertbackground=CYAN, relief="flat",
                                  font=self.f["editor"], padx=S(14), pady=S(12), wrap="word",
                                  undo=True, selectbackground=SELECT, highlightthickness=0)
        sb = ttk.Scrollbar(box, orient="vertical", command=self.setup_text.yview)
        self.setup_text.configure(yscrollcommand=sb.set)
        self.setup_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.setup_text.tag_configure("comment", foreground=DIM)
        self.setup_text.bind("<KeyRelease>", lambda e: self._highlight_setup())
        row = tk.Frame(inner, bg=VOID)
        row.pack(fill="x", pady=(S(12), 0))
        FlatButton(row, "Save setup", self.save_setup, "primary", self.f["strong"]).pack(side="left")
        FlatButton(row, "Undo changes", self.load_setup, "ghost", self.f["button"]).pack(side="left", padx=S(8))
        self.setup_msg = tk.Label(row, text="", bg=VOID, fg=MUTED, font=self.f["small"])
        self.setup_msg.pack(side="left", padx=S(8))
        self.keep_lbl = tk.Label(inner, text="", bg=VOID, fg=MUTED, font=self.f["small"], justify="left",
                                 wraplength=S(760), anchor="w")
        self.keep_lbl.pack(fill="x", pady=(S(10), 0))
        self._update_keep_label()
        self.load_setup()
        return page

    def _update_keep_label(self):
        keep = self.cfg["keep"]
        if keep:
            self.keep_lbl.configure(text="Marked as needed in RAMCheck: " + ", ".join(sorted(keep)) +
                                         ". These are never flagged or cleaned up. Remove a mark in the program's details.")
        else:
            self.keep_lbl.configure(text="Tip: in a program's details you can click Mark as needed. "
                                         "Marked programs are never flagged or cleaned up.")

    def _highlight_setup(self):
        t = self.setup_text
        t.tag_remove("comment", "1.0", "end")
        for i, line in enumerate(t.get("1.0", "end").splitlines(), start=1):
            if line.strip().startswith("#"):
                t.tag_add("comment", f"{i}.0", f"{i}.end")

    def load_setup(self):
        self.setup_text.delete("1.0", "end")
        self.setup_text.insert("1.0", core.read_setup_text())
        self._highlight_setup()
        self.setup_msg.configure(text="")

    def save_setup(self):
        text = self.setup_text.get("1.0", "end-1c")
        core.write_setup_text(text)
        n = len(core.setup_lines(text))
        msg = f"Saved. {n} fact{'s' if n != 1 else ''} will be sent with the next analysis."
        if self.verdicts:
            msg += " Analyze again to apply them."
        fade_label(self.setup_msg, msg, MUTED, VOID, 6000)

    # ----------------------------------------------------- settings page ---

    def _build_settings(self, parent):
        page = tk.Frame(parent, bg=VOID)
        outer, inner = scrollable(page, VOID, self.root)
        outer.pack(fill="both", expand=True)
        inner.configure(padx=S(20), pady=S(18))
        inner.columnconfigure(1, weight=1)
        self.ai_rows = {}

        def section(row, text):
            tk.Label(inner, text=text, bg=VOID, fg=TEXT, font=self.f["title"]).grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(S(18) if row else 0, S(8)))

        def label(row, text):
            w = tk.Label(inner, text=text, bg=VOID, fg=MUTED, font=self.f["body"])
            w.grid(row=row, column=0, sticky="nw", pady=S(7), padx=(0, S(24)))
            return w

        def hint(parent_, text=""):
            return tk.Label(parent_, text=text, bg=VOID, fg=DIM, font=self.f["small"],
                            justify="left", wraplength=S(600))

        def box(row):
            b = tk.Frame(inner, bg=VOID)
            b.grid(row=row, column=1, sticky="w", pady=S(4))
            return b

        section(0, "AI")
        label(1, "Where it runs")
        seg = box(1)
        self.where_seg = Segmented(seg, (("cloud", "In the cloud (API key)"), ("local", "On this PC (free, private)")),
                                   self._set_where, self.f["button"])
        self.where_seg.pack(anchor="w")

        label(2, "Service")
        svc = box(2)
        self.provider_box = ttk.Combobox(svc, state="readonly", width=32, font=self.f["body"])
        self.provider_box.pack(anchor="w")
        self.provider_box.bind("<<ComboboxSelected>>", lambda e: (self.provider_box.selection_clear(),
                                                                 self._select_provider(
                                                                     self._provider_by_name.get(self.provider_box.get()))))
        self.provider_hint = hint(svc)
        self.provider_hint.pack(anchor="w", pady=(S(4), 0))

        # API key
        lbl = label(3, "API key")
        key_box = box(3)
        self.key_state = tk.Label(key_box, text="", bg=VOID, fg=TEXT, font=self.f["body"])
        self.key_state.pack(anchor="w")
        key_row = tk.Frame(key_box, bg=VOID)
        key_row.pack(anchor="w", pady=(S(6), 0))
        self.key_entry = styled_entry(key_row, self.f["body"], width=44, show="•")
        self.key_entry.pack(side="left", ipady=S(5))
        FlatButton(key_row, "Save key", self.save_key, "ghost", self.f["button"]).pack(side="left", padx=S(8))
        self.btn_remove_key = FlatButton(key_row, "Remove saved key", self.remove_key, "quiet", self.f["button"])
        self.btn_remove_key.pack(side="left")
        self.key_link = tk.Label(key_box, text="", bg=VOID, fg=CYAN, font=self.f["small"] + ("underline",),
                                 cursor="hand2")
        self.key_link.pack(anchor="w", pady=(S(6), 0))
        self.key_link.bind("<Button-1>", lambda e: webbrowser.open(core.PROVIDERS[self.pend["provider"]]["key_url"]))
        self.key_hint = hint(key_box)
        self.key_hint.pack(anchor="w", pady=(S(2), 0))
        self.ai_rows["key"] = (lbl, key_box)

        # address
        lbl = label(4, "Address")
        url_box = box(4)
        self.url_entry = styled_entry(url_box, self.f["body"], width=44)
        self.url_entry.pack(anchor="w", ipady=S(5))
        self.url_hint = hint(url_box)
        self.url_hint.pack(anchor="w", pady=(S(4), 0))
        self.ai_rows["url"] = (lbl, url_box)

        # local status
        lbl = label(5, "Status")
        st_box = box(5)
        self.local_state = tk.Label(st_box, text="", bg=VOID, fg=MUTED, font=self.f["body"], justify="left",
                                    wraplength=S(600))
        self.local_state.pack(anchor="w")
        st_row = tk.Frame(st_box, bg=VOID)
        st_row.pack(anchor="w", pady=(S(6), 0))
        FlatButton(st_row, "Check again", self.check_local, "ghost", self.f["button"]).pack(side="left")
        self.get_local_btn = FlatButton(st_row, "", lambda: webbrowser.open(core.PROVIDERS[self.pend["provider"]]["key_url"]),
                                        "quiet", self.f["button"])
        self.get_local_btn.pack(side="left", padx=S(8))
        self.ai_rows["status"] = (lbl, st_box)

        # model
        label(6, "Model")
        m_box = box(6)
        m_row = tk.Frame(m_box, bg=VOID)
        m_row.pack(anchor="w")
        self.model_box = ttk.Combobox(m_row, width=40, font=self.f["body"])
        self.model_box.pack(side="left")
        self.model_box.bind("<<ComboboxSelected>>", lambda e: (self.model_box.selection_clear(),
                                                               self._update_preset_text(self.preset_seg.get())))
        self.load_models_btn = FlatButton(m_row, "Load models", self.load_models, "ghost", self.f["button"])
        self.load_models_btn.pack(side="left", padx=S(8))
        self.model_msg = hint(m_box, "")
        self.model_msg.pack(anchor="w", pady=(S(4), 0))

        # ollama download
        lbl = label(7, "Download a model")
        dl_box = box(7)
        dl_row = tk.Frame(dl_box, bg=VOID)
        dl_row.pack(anchor="w")
        self._pull_names = {f"{n}   ({size} download, needs {ram} RAM)": n for n, size, ram in core.OLLAMA_SUGGESTIONS}
        self.pull_box = ttk.Combobox(dl_row, values=list(self._pull_names), width=46, font=self.f["body"])
        self.pull_box.current(0)
        self.pull_box.pack(side="left")
        self.pull_btn = FlatButton(dl_row, "Download", self.pull_model, "ghost", self.f["button"])
        self.pull_btn.pack(side="left", padx=S(8))
        self.pull_msg = hint(dl_box, "The first one is a good start. You can also type any model name from "
                                     "ollama.com/library.")
        self.pull_msg.pack(anchor="w", pady=(S(4), 0))
        self.ai_rows["pull"] = (lbl, dl_box)

        section(8, "Analysis")
        c = self.cfg
        label(9, "Preset")
        pbox = box(9)
        self.preset_seg = Segmented(pbox, [(k, p["name"]) for k, p in PRESETS.items()] + [("custom", "Custom")],
                                    self._apply_preset, self.f["button"], value="balanced")
        self.preset_seg.pack(anchor="w")
        card = tk.Frame(pbox, bg=PANEL)
        card.pack(anchor="w", fill="x", pady=(S(8), 0))
        self.preset_desc = tk.Label(card, text="", bg=PANEL, fg=TEXT, font=self.f["body"], justify="left",
                                    wraplength=S(560), anchor="w")
        self.preset_desc.pack(anchor="w", padx=S(14), pady=(S(10), S(2)))
        self.preset_est = tk.Label(card, text="", bg=PANEL, fg=MUTED, font=self.f["small"], justify="left",
                                   wraplength=S(560), anchor="w")
        self.preset_est.pack(anchor="w", padx=S(14), pady=(0, S(6)))
        self.preset_cmp = tk.Label(card, text="", bg=PANEL, fg=DIM, font=self.f["small"], justify="left",
                                   wraplength=S(560), anchor="w")
        self._applying_preset = False

        label(10, "Programs to assess")
        b10 = box(10)
        self.top_slider = StopSlider(b10, [10, 15, 20, 25, 30, 40, 50, 60, 70, 80], c["top"],
                                     lambda v: f"{v} programs", self.f["body"], command=lambda v: self._sync_preset())
        self.top_slider.pack(anchor="w")
        hint(b10, "The biggest ones get assessed. More means a fuller picture and a slightly longer, "
                  "pricier run.").pack(anchor="w", pady=(S(2), 0))
        label(11, "Refresh every")
        b11 = box(11)
        self.refresh_slider = StopSlider(b11, [3, 5, 10, 15, 30, 60, 120], c["refresh_s"],
                                         lambda v: f"{v} seconds" if v < 60 else f"{v // 60} minute{'s' if v >= 120 else ''}",
                                         self.f["body"], command=lambda v: self._sync_preset())
        self.refresh_slider.pack(anchor="w")
        hint(b11, "How often the list and memory map update. RAMCheck pauses measuring while it's minimized.").pack(
            anchor="w", pady=(S(2), 0))
        label(12, "Hide programs under")
        b12 = box(12)
        self.minmb_slider = StopSlider(b12, [0, 5, 10, 25, 50, 100, 250, 500], c["min_mb"],
                                       lambda v: "Show all" if v == 0 else f"{v} MB", self.f["body"],
                                       command=lambda v: self._sync_preset())
        self.minmb_slider.pack(anchor="w")
        hint(b12, "Tiny background processes stay out of the list and aren't sent to the AI.").pack(
            anchor="w", pady=(S(2), 0))
        label(13, "Double-check")
        dc_box = box(13)
        dc_row = tk.Frame(dc_box, bg=VOID)
        dc_row.pack(anchor="w")
        self.dc_switch = Switch(dc_row, c.get("double_check", True), self._set_double_check)
        self.dc_switch.pack(side="left")
        self.dc_state = tk.Label(dc_row, text="", bg=VOID, fg=TEXT, font=self.f["body"])
        self.dc_state.pack(side="left", padx=(S(10), 0))
        hint(dc_box, "A second, stricter AI pass over everything marked bloatware or optional to catch "
                     "false alarms. Adds a few seconds, and a fraction of a cent with paid APIs.").pack(anchor="w", pady=(S(4), 0))

        section(14, "App")
        label(15, "Updates")
        up_box = box(15)
        up_row = tk.Frame(up_box, bg=VOID)
        up_row.pack(anchor="w")
        store = core.install_mode() == "store"
        self.update_switch = Switch(up_row, c.get("check_updates", True) and not store)
        if not store:
            self.update_switch.pack(side="left")
        tk.Label(up_row, text="Updates arrive automatically through the Microsoft Store" if store else
                 "Tell me when a new version is out", bg=VOID, fg=TEXT,
                 font=self.f["body"]).pack(side="left", padx=(0 if store else S(10), 0))
        if not store:
            hint(up_box, "Checks the public GitHub release page once per start. Nothing else is sent.").pack(
                anchor="w", pady=(S(4), 0))
        check_row = tk.Frame(up_box, bg=VOID)
        check_row.pack(anchor="w", pady=(S(10), 0))
        if store:
            FlatButton(check_row, "Open Microsoft Store updates",
                       lambda: self._open_folder("ms-windows-store://downloadsandupdates"), "ghost",
                       self.f["button"]).pack(side="left")
        else:
            self.check_btn = FlatButton(check_row, "Check for updates", self.check_updates_now, "ghost",
                                        self.f["button"])
            self.check_btn.pack(side="left")
            self.update_action = FlatButton(check_row, "", self._update_action, "primary", self.f["strong"])
            self.update_msg = tk.Label(up_box, text=f"You have RAMCheck {core.VERSION}.", bg=VOID, fg=MUTED,
                                       font=self.f["small"], justify="left", wraplength=S(600), anchor="w")
            self.update_msg.pack(anchor="w", pady=(S(6), 0))
        label(16, "Help")
        help_box = box(16)
        help_row = tk.Frame(help_box, bg=VOID)
        help_row.pack(anchor="w")
        FlatButton(help_row, "Report a problem", lambda: webbrowser.open(core.REPO_URL + "/issues"),
                   "ghost", self.f["button"]).pack(side="left")
        FlatButton(help_row, "Open data folder", lambda: self._open_folder(core.app_dir()),
                   "quiet", self.f["button"]).pack(side="left", padx=S(8))
        hint(help_box, "If something breaks, error.log in the data folder has the details. Attaching it to "
                       "a report helps a lot. It contains no API keys.").pack(anchor="w", pady=(S(4), 0))

        row = tk.Frame(inner, bg=VOID)
        row.grid(row=17, column=0, columnspan=2, sticky="w", pady=(S(22), 0))
        FlatButton(row, "Save settings", self.save_settings, "primary", self.f["strong"]).pack(side="left")
        self.settings_msg = tk.Label(row, text="", bg=VOID, fg=MUTED, font=self.f["small"])
        self.settings_msg.pack(side="left", padx=S(12))

        foot = tk.Frame(inner, bg=VOID)
        foot.grid(row=18, column=0, columnspan=2, sticky="w", pady=(S(28), 0))
        mode = core.install_mode()
        mode_text = {"installed": "installed version", "portable": "portable version, nothing installed",
                     "source": "running from source", "store": "Microsoft Store version"}[mode]
        tk.Label(foot, text=f"RAMCheck {core.VERSION}, {mode_text}. Settings, setup notes and API keys are "
                            f"stored in {core.app_dir()}", bg=VOID, fg=DIM, font=self.f["small"],
                 justify="left", wraplength=S(760)).pack(anchor="w")
        if mode == "portable":
            link = tk.Label(foot, text="Want it in your Start menu? Get the installer from the releases page",
                            bg=VOID, fg=CYAN, font=self.f["small"] + ("underline",), cursor="hand2")
            link.pack(anchor="w", pady=(S(4), 0))
            link.bind("<Button-1>", lambda e: webbrowser.open(core.REPO_URL + "/releases"))

        self._load_settings_fields()
        return page

    # settings state: edits stay in self.pend until "Save settings"
    def _load_settings_fields(self):
        c = self.cfg
        self.pend = {"provider": c["provider"], "models": dict(c["models"]), "urls": dict(c["urls"]),
                     "double_check": c.get("double_check", True)}
        self._last_cloud = c["provider"] if core.PROVIDERS[c["provider"]]["where"] == "cloud" else "claude"
        self.top_slider.set(c["top"])
        self.refresh_slider.set(c["refresh_s"])
        self.minmb_slider.set(c["min_mb"])
        self.dc_switch.set(self.pend["double_check"], animate=False)
        self._applying_preset = False
        self._set_double_check(self.pend["double_check"])
        self.preset_seg.set(self._matching_preset(), animate=False)
        self._show_provider()

    def _pending_cfg(self):
        self._commit_fields()
        return dict(self.cfg, provider=self.pend["provider"], models=dict(self.pend["models"]),
                    urls=dict(self.pend["urls"]))

    def _commit_fields(self):
        p = self.pend["provider"]
        model = self.model_box.get().strip()
        if model:
            self.pend["models"][p] = model
        if p in ("custom", "ollama", "lmstudio"):
            url = self.url_entry.get().strip()
            if url and url != core.PROVIDERS[p]["url"]:
                self.pend["urls"][p] = url
            else:
                self.pend["urls"].pop(p, None)

    def _set_where(self, where):
        if core.PROVIDERS[self.pend["provider"]]["where"] == where:
            return
        self._select_provider(self._last_cloud if where == "cloud" else "ollama")

    def _select_provider(self, provider):
        if not provider:
            return
        self._commit_fields()
        self.pend["provider"] = provider
        if core.PROVIDERS[provider]["where"] == "cloud":
            self._last_cloud = provider
        self._show_provider()

    def _show_provider(self):
        p = self.pend["provider"]
        info = core.PROVIDERS[p]
        where = info["where"]
        if self.where_seg.get() != where:
            self.where_seg.set(where)
        group = [(k, v["name"]) for k, v in core.PROVIDERS.items() if v["where"] == where]
        self._provider_by_name = {name: k for k, name in group}
        self.provider_box.configure(values=[name for _, name in group])
        self.provider_box.set(info["name"])
        self.provider_hint.configure(text=info["hint"])

        show = {"key": where == "cloud", "url": p in ("custom", "ollama", "lmstudio"),
                "status": where == "local", "pull": p == "ollama"}
        for name, (lbl, widget) in self.ai_rows.items():
            (lbl.grid if show[name] else lbl.grid_remove)()
            (widget.grid if show[name] else widget.grid_remove)()

        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, self.pend["urls"].get(p) or info["url"])
        self.url_hint.configure(text="Ends in /v1 for most services, e.g. https://api.groq.com/openai/v1"
                                if p == "custom" else "Only change this if it runs on another PC or port.")
        self.model_box.configure(values=info["models"])
        self.model_box.set(self.pend["models"].get(p) or (info["models"] or [""])[0])
        self.model_msg.configure(text="Model names change often. Load models shows what's available right now."
                                 if where == "cloud" else "", fg=DIM)
        if info["key_url"] and where == "cloud":
            self.key_link.configure(text=f"Get a key at {info['key_url'].split('/')[2]}")
            self.key_link.pack(anchor="w", pady=(S(6), 0), before=self.key_hint)
        else:
            self.key_link.pack_forget()
        self.key_hint.configure(text=("Optional for this one. Leave it empty if the service doesn't need a key. "
                                      if p == "custom" else "Billed per use by the provider. ")
                                + ("Keys are stored encrypted, readable only by your Windows account on this PC."
                                   if os.name == "nt" else "Keys are stored only on this PC."))
        self.get_local_btn.configure(text=f"Get {info['name']}")
        self._update_key_state()
        if hasattr(self, "preset_seg"):
            self._update_preset_text(self.preset_seg.get())
        if where == "local":
            self.check_local()

    def _set_double_check(self, on):
        self.pend["double_check"] = on
        self.dc_state.configure(text="On" if on else "Off", fg=TEXT if on else MUTED)
        self._sync_preset()

    def _current_values(self):
        return {"top": self.top_slider.get(), "refresh_s": self.refresh_slider.get(),
                "min_mb": self.minmb_slider.get(), "double_check": self.pend.get("double_check", True)}

    def _matching_preset(self):
        cur = self._current_values()
        for key, p in PRESETS.items():
            if all(p[k] == cur[k] for k in cur):
                return key
        return "custom"

    def _apply_preset(self, key):
        if key == "custom":
            self._update_preset_text("custom")
            return
        p = PRESETS[key]
        self._applying_preset = True  # don't flip to "Custom" while the sliders move one by one
        self.top_slider.set(p["top"], animate=True)
        self.refresh_slider.set(p["refresh_s"], animate=True)
        self.minmb_slider.set(p["min_mb"], animate=True)
        if self.dc_switch.get() != p["double_check"]:
            self.dc_switch.set(p["double_check"])
        self.pend["double_check"] = p["double_check"]
        self.dc_state.configure(text="On" if p["double_check"] else "Off",
                                fg=TEXT if p["double_check"] else MUTED)
        self._applying_preset = False
        self._update_preset_text(key)

    def _sync_preset(self):
        if getattr(self, "_applying_preset", True) or not hasattr(self, "preset_seg"):
            return
        key = self._matching_preset()
        if self.preset_seg.get() != key:
            self.preset_seg.set(key)
        self._update_preset_text(key)

    def _update_preset_text(self, key):
        if not hasattr(self, "preset_desc"):
            return
        self.preset_desc.configure(text=PRESETS[key]["desc"] if key in PRESETS else CUSTOM_DESC)
        cur = self._current_values()
        p = self.pend["provider"]
        model = self.model_box.get().strip() if hasattr(self, "model_box") else core.model_for(self.cfg, p)
        prices = getattr(self, "prices", {})
        self.preset_est.configure(text=estimate_text(cur["top"], cur["double_check"], p, model, prices))
        compare = preset_costs(p, model, prices)
        self.preset_cmp.configure(text=compare)
        if compare:
            self.preset_cmp.pack(anchor="w", padx=S(14), pady=(0, S(10)))
        else:
            self.preset_cmp.pack_forget()

    def _update_key_state(self):
        p = self.pend["provider"]
        key, source = core.resolve_api_key(self.cfg, p)
        env = core.PROVIDERS[p]["env"]
        if source == "environment":
            text, color = f"Using {env} from Windows, ending in {key[-4:]}", TEXT
        elif source == "saved":
            text, color = f"Saved key ending in {key[-4:]}", TEXT
        elif p == "custom":
            text, color = "No key saved (fine if the service doesn't need one).", MUTED
        else:
            text, color = "No key yet. Paste one below.", "#ffc857"
        self.key_state.configure(text=text, fg=color)
        self.btn_remove_key.set_enabled(source == "saved")

    def save_key(self):
        key = self.key_entry.get().strip()
        if not key:
            self.settings_msg.configure(text="Paste a key first.", fg="#ffc857")
            return
        self.cfg["api_keys"][self.pend["provider"]] = key
        core.save_config(self.cfg)
        self.key_entry.delete(0, "end")
        self._update_key_state()
        fade_label(self.settings_msg, f"{core.PROVIDERS[self.pend['provider']]['name']} key saved.", MUTED, VOID, 4000)

    def remove_key(self):
        self.cfg["api_keys"].pop(self.pend["provider"], None)
        core.save_config(self.cfg)
        self._update_key_state()
        fade_label(self.settings_msg, "Saved key removed.", MUTED, VOID, 4000)

    def load_models(self):
        p, cfg = self.pend["provider"], self._pending_cfg()
        self.model_msg.configure(text="Loading ...", fg=MUTED)

        def work():
            try:
                self.q.put(("models", p, core.list_models(cfg, p), ""))
            except core.AIError as e:
                self.q.put(("models", p, None, str(e)))
        threading.Thread(target=work, daemon=True).start()

    def _models_loaded(self, p, models, error):
        if p != self.pend["provider"]:
            return
        if error:
            self.model_msg.configure(text=error, fg="#ffc857")
            return
        if not models:
            self.model_msg.configure(text="No models found.", fg="#ffc857")
            return
        self.model_box.configure(values=models)
        if self.model_box.get().strip() not in models:
            preferred = [m for m in core.PROVIDERS[p]["models"] if m in models]
            self.model_box.set(preferred[0] if preferred else models[0])
        self.model_msg.configure(text=f"{len(models)} model{'s' if len(models) != 1 else ''} available. "
                                      "Pick one from the list.", fg=MUTED)

    def check_local(self):
        p, cfg = self.pend["provider"], self._pending_cfg()
        self.local_state.configure(text="Checking ...", fg=MUTED)

        def work():
            running, text = core.local_status(cfg, p)
            models = []
            if running:
                try:
                    models = core.list_models(cfg, p)
                except core.AIError:
                    pass
            self.q.put(("local_status", p, running, text, models))
        threading.Thread(target=work, daemon=True).start()

    def _local_checked(self, p, running, text, models):
        if p != self.pend["provider"]:
            return
        self.local_state.configure(text=text, fg=(TEXT if running and models else "#ffc857"))
        self.get_local_btn.set_enabled(not running)
        self.pull_btn.set_enabled(running and not getattr(self, "pulling", False))
        if models:
            self._models_loaded(p, models, "")

    def pull_model(self):
        choice = self.pull_box.get().strip()
        model = self._pull_names.get(choice, choice.split()[0] if choice else "")
        if not model:
            return
        self.pulling = True
        self.pull_btn.set_enabled(False)
        cfg = self._pending_cfg()

        def work():
            try:
                core.ollama_pull(cfg, model, lambda t: self.q.put(("pull_progress", t)))
                self.q.put(("pull_done", True, model))
            except core.AIError as e:
                self.q.put(("pull_done", False, str(e)))
        threading.Thread(target=work, daemon=True).start()

    def _pull_done(self, ok, text):
        self.pulling = False
        self.pull_btn.set_enabled(True)
        if ok:
            self.pend["models"]["ollama"] = text
            self.pull_msg.configure(text=f"{text} is ready. Click Save settings to use it.", fg=MUTED)
            self.check_local()
            self.model_box.set(text)
        else:
            self.pull_msg.configure(text=text, fg="#ffc857")

    def save_settings(self):
        top, refresh, min_mb = self.top_slider.get(), self.refresh_slider.get(), self.minmb_slider.get()
        self._commit_fields()
        self.cfg.update({
            "provider": self.pend["provider"], "models": dict(self.pend["models"]),
            "urls": dict(self.pend["urls"]), "top": top, "refresh_s": refresh, "min_mb": min_mb,
            "double_check": self.pend["double_check"], "check_updates": self.update_switch.get(),
        })
        core.save_config(self.cfg)
        name = core.PROVIDERS[self.cfg["provider"]]["name"]
        fade_label(self.settings_msg, f"Saved. The next analysis uses {name} ({core.model_for(self.cfg)}).",
                   MUTED, VOID, hold_ms=5000)
        self.refresh_table()

    # ---------------------------------------------------------- navigation ---

    def load_prices(self):
        if getattr(self, "_prices_loading", False):
            return
        self._prices_loading = True
        self.prices = core.load_prices(fetch=False)  # cached copy right away
        threading.Thread(target=lambda: self.q.put(("prices", core.load_prices(fetch=True))), daemon=True).start()

    def show_page(self, key):
        if key == "settings":
            self.load_prices()
        if key == "memory":
            self._update_tiles(core.memory_status())
            self._update_test_plan()
            if self.hw is None:
                self.hw = {}
                threading.Thread(target=self._load_hardware, daemon=True).start()
        self.pages[key].tkraise()
        self.tabbar.set(key)
        if key == "setup":
            self.setup_msg.configure(text="")
        if key == "settings":
            self.settings_msg.configure(text="")

    # ----------------------------------------------------------- measuring ---

    def _measure_loop(self):
        while not self.stop.is_set():
            if self.minimized and not self.refresh_now.is_set():
                time.sleep(1)  # don't burn CPU measuring while nobody is looking
                continue
            try:
                procs = core.collect(fast=False)
                self.q.put(("procs", procs, core.memory_status()))
            except Exception as e:  # never let the thread die silently
                self.q.put(("status", f"Measuring failed: {e}", MAGENTA))
            self.refresh_now.wait(timeout=self.cfg.get("refresh_s", 8))
            self.refresh_now.clear()

    def refresh(self):
        self.refresh_now.set()
        self.set_status("Measuring ...")

    def _poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "procs":
                    first = not self.procs
                    self.procs, self.mem = msg[1], msg[2]
                    self._track_growth()
                    self._remap_startup()
                    self.refresh_table()
                    self.draw_map(reveal=first)
                    self.render_detail()
                    if first:
                        self.btn_analyze.set_enabled(True)
                        self.rescan_startup()
                    if first and self.verdicts:
                        self._update_cleanup_button()
                        saved = core.savings(self.procs, self.verdicts) / core.MB
                        self.savings_lbl.configure(text=f"Possible savings about {saved:,.0f} MB")
                        self.set_status(f"Loaded your analysis from {self.analyzed_at:%H:%M}. "
                                        "Analyze again for a fresh one.")
                    elif not self.busy:
                        self.set_status(f"{len(self.procs)} programs running. Updated "
                                        f"{dt.datetime.now():%H:%M:%S}", quiet=True)
                elif kind == "analysis":
                    self._apply_analysis(*msg[1:])
                elif kind == "ai_error":
                    self._analysis_failed(msg[1])
                elif kind == "status":
                    self.set_status(msg[1], msg[2])
                elif kind == "ended":
                    self._after_end(*msg[1:])
                elif kind == "startup":
                    self.startup_entries, self.startup_scanned = msg[1], True
                    self._remap_startup()
                    self.refresh_startup_table()
                    self.refresh_table()
                    self.render_detail(force=True)
                elif kind == "startup_changed":
                    ok, text = msg[1], msg[2]
                    self._startup_note = (text, ok)
                    self.set_status(text, MUTED if ok else MAGENTA)
                    self.rescan_startup()
                elif kind == "progress":
                    self.progress_text = msg[1]
                elif kind == "prices":
                    self.prices = msg[1] or getattr(self, "prices", {})
                    if hasattr(self, "preset_seg"):
                        self._update_preset_text(self.preset_seg.get())
                    self.render_detail(force=True)
                elif kind == "answer":
                    self._got_answer(*msg[1:])
                elif kind == "hw":
                    self.hw = msg[1]
                    self._render_hw()
                elif kind == "update" and msg[1]:
                    version, url = msg[1]
                    self.update_lbl.configure(text=f"RAMCheck {version} is available")
                    self.update_info = {"state": "update", "version": version, "url": url}
                    self.update_lbl.bind("<Button-1>", lambda e: self._show_update())
                elif kind == "update_checked":
                    self._update_checked(msg[1])
                elif kind == "update_progress":
                    self.update_msg.configure(text=msg[1], fg=MUTED)
                elif kind == "update_ready":
                    self._update_ready(msg[1], msg[2])
                elif kind == "models":
                    self._models_loaded(*msg[1:])
                elif kind == "local_status":
                    self._local_checked(*msg[1:])
                elif kind == "pull_progress":
                    self.pull_msg.configure(text=msg[1], fg=MUTED)
                elif kind == "pull_done":
                    self._pull_done(*msg[1:])
                elif kind == "cleanup_done":
                    if self.cleanup_dialog:
                        self.cleanup_dialog.show_result(*msg[1:])
                    self.rescan_startup()
                    self.refresh()
        except queue.Empty:
            pass
        if not self.stop.is_set():
            self.root.after(100, self._poll)

    def _tick_live(self):
        try:
            self.minimized = self.root.state() == "iconic"
        except tk.TclError:
            pass
        mem = core.memory_status()
        self.history.append(mem["percent"])
        self.headline.configure(text=f"{mem['used'] / core.GB:.1f} of {mem['total'] / core.GB:.1f} GB "
                                     f"in use ({mem['percent']:.0f} %)")
        self.subline.configure(text=f"{mem['available'] / core.GB:.1f} GB free for new programs")
        if self.tabbar.active == "memory":
            self._update_tiles(mem)
        self.draw_graph()
        if not self.stop.is_set():
            self.root.after(1000, self._tick_live)

    def set_status(self, text, color=MUTED, quiet=False):
        if quiet:  # routine updates shouldn't blink every few seconds
            self.status.__dict__["_msg"] = self.status.__dict__.get("_msg", 0) + 1
            self.status.configure(text=text, fg=color)
        elif text != self.status.cget("text"):
            fade_label(self.status, text, color, VOID)
        else:
            self.status.configure(fg=color)

    def start_loading(self):
        self._loading += 1
        if self._loading == 1:
            self._loader_t0 = time.perf_counter()
            self._loader_step()

    def stop_loading(self):
        self._loading = max(0, self._loading - 1)

    def _loader_step(self):
        w = self.loader.winfo_width()
        if not self._loading:
            self.loader.coords(self.loader_bar, 0, 0, 0, S(2))
            return
        phase = ((time.perf_counter() - self._loader_t0) / 1.4) % 1.0  # one sweep every 1.4 s
        x = -0.3 * w + ease(phase) * 1.3 * w
        self.loader.coords(self.loader_bar, x, 0, x + 0.3 * w, S(2))
        self.root.after(16, self._loader_step)

    # --------------------------------------------------------------- graph ---

    def draw_graph(self):
        c = self.graph
        c.delete("all")
        w, h = int(c.cget("width")), int(c.cget("height"))
        c.create_line(0, h - 1, w, h - 1, fill=LINE)
        if len(self.history) < 2:
            return
        n = self.history.maxlen
        step = w / (n - 1)
        offset = n - len(self.history)
        pts = []
        for i, pct in enumerate(self.history):
            pts += [(offset + i) * step, h - 2 - (h - 4) * pct / 100]
        c.create_polygon(pts[0], h, *pts, pts[-2], h, fill="#143447", outline="")
        c.create_line(*pts, fill=CYAN, width=max(1, S(1.5)))

    # ---------------------------------------------------------------- map ---

    MAP_COLS, MAP_ROWS = 64, 8

    def _ordered_for_map(self):
        if self.verdicts:
            order = list(core.CATEGORIES)

            def key(g):
                v = self.verdicts.get(g["key"])
                return (order.index(v["category"]) if v else len(order), -g["mem"])
            return sorted(self.procs, key=key)
        return list(self.procs)

    def draw_map(self, reveal=False):
        """Colours every cell. Items are created once and only recoloured, so hovering stays smooth.
        reveal=True plays the one bigger animation: new colours sweep across the grid."""
        c = self.map
        W, H = c.winfo_width(), c.winfo_height()
        if W < 50:
            return
        if not self.mem:
            if not getattr(self, "_map_wait", None):
                c.delete("all")
                self._map_items = None
                self._map_wait = c.create_text(0, H / 2, anchor="w", fill=MUTED, font=self.f["body"],
                                               text="Measuring every running program. This takes a few seconds ...")
            return
        if getattr(self, "_map_wait", None):
            c.delete(self._map_wait)
            self._map_wait = None
        cols, rows = self.MAP_COLS, self.MAP_ROWS
        total_cells = cols * rows
        per = self.mem["total"] / total_cells

        owner = [None] * total_cells
        colors = [None] * total_cells
        idx, cum, alt = 0, 0.0, {}
        has_skipped = False
        proc_sum = 0
        for g in self._ordered_for_map():
            proc_sum += g["mem"]
            cum += g["mem"] / per
            n = min(int(round(cum)) - idx, total_cells - idx)
            if n <= 0:
                continue
            v = self.verdicts.get(g["key"])
            cat = v["category"] if v else None
            pair = CAT_COLORS[cat] if cat else (NOT_ASSESSED if self.verdicts else UNRATED)
            if not cat and self.verdicts:
                cat = "__not_assessed"
                has_skipped = True
            flip = alt.get(cat, 0)
            alt[cat] = 1 - flip
            for i in range(idx, idx + n):
                owner[i], colors[i] = g["key"], pair[flip]
            idx += n
        windows_cells = int(round(max(0, self.mem["used"] - proc_sum) / per))
        for i in range(idx, min(total_cells, idx + windows_cells)):
            owner[i], colors[i] = "__shared", SHARED_CELL
        self.cell_owner = owner
        self._draw_legend(has_skipped)

        self._ensure_map_items(W, H)
        self._map_target = colors
        if reveal and ANIMATE:
            self._map_from = list(getattr(self, "_map_shown", [None] * total_cells))
            self._reveal_t0 = time.perf_counter()
            if not getattr(self, "_revealing", False):
                self._revealing = True
                self._reveal_step()
        elif not getattr(self, "_revealing", False):
            self._apply_cells(colors)

    def _ensure_map_items(self, W, H):
        if getattr(self, "_map_items", None) and self._map_size == (W, H):
            return
        c = self.map
        c.delete("all")
        cols, rows = self.MAP_COLS, self.MAP_ROWS
        gap = max(1, S(2))
        cw = (W - gap * (cols - 1)) / cols
        ch = (H - gap * (rows - 1)) / rows
        dot = max(1, S(1))
        self._map_items, self._map_state = [], []
        for i in range(cols * rows):
            r, col = divmod(i, cols)
            x, y = col * (cw + gap), r * (ch + gap)
            rect = c.create_rectangle(x, y, x + cw, y + ch, width=0, state="hidden")
            cx, cy = x + cw / 2, y + ch / 2
            d = c.create_rectangle(round(cx - dot), round(cy - dot), round(cx - dot) + 2 * dot,
                                   round(cy - dot) + 2 * dot, fill=DIM, width=0)
            self._map_items.append((rect, d))
            self._map_state.append(None)
        self._map_size = (W, H)
        self._map_shown = [None] * (cols * rows)

    def _apply_cells(self, colors):
        c = self.map
        sel, hov = self.selected, self.hover_key
        for i, color in enumerate(colors):
            k = self.cell_owner[i] if i < len(self.cell_owner) else None
            outline = (TEXT if k == sel else "#b8b2e6" if k == hov else "") if color and k else ""
            state = (color, outline)
            if self._map_state[i] == state:
                continue  # only touch cells that actually changed
            rect, dot = self._map_items[i]
            if color:
                c.itemconfigure(rect, fill=color, outline=outline, width=S(1.5) if outline else 0, state="normal")
                c.itemconfigure(dot, state="hidden")
            else:
                c.itemconfigure(rect, state="hidden")
                c.itemconfigure(dot, state="normal")
            self._map_state[i] = state
        self._map_shown = list(colors)

    def _reveal_step(self):
        """A diagonal wave: each cell switches to its new colour with a short bright glint."""
        cols, rows = self.MAP_COLS, self.MAP_ROWS
        p = (time.perf_counter() - self._reveal_t0) / 0.9  # 0.9 s for the whole sweep
        out = []
        for i, new in enumerate(self._map_target):
            r, col = divmod(i, cols)
            start = (col / cols) * 0.75 + (r / rows) * 0.25
            local = (p * 1.25 - start) / 0.12
            old = self._map_from[i] if i < len(self._map_from) else None
            if local <= 0:
                out.append(old)
            elif local >= 1 or not new:
                out.append(new)
            else:
                out.append(mix("#ffffff", new, ease(local)) if new else old)
        try:
            self._apply_cells(out)
        except tk.TclError:
            return
        if p < 1.0:
            self.root.after(16, self._reveal_step)
        else:
            self._revealing = False
            self._apply_cells(self._map_target)

    def _draw_legend(self, has_skipped=False):
        items = []
        if self.verdicts:
            present = {v["category"] for v in self.verdicts.values()}
            items += [(CAT_COLORS[c][0], label) for c, label in core.CATEGORIES.items() if c in present]
        else:
            items.append((CYAN, "Programs"))
        if has_skipped:
            items.append((NOT_ASSESSED[0], "Not assessed"))
        items += [(SHARED_CELL, "Shared and kernel"), (None, "Free")]
        if items == getattr(self, "_legend_items", None):
            return  # unchanged, don't rebuild on every hover
        self._legend_items = items
        for w in self.legend.winfo_children():
            w.destroy()
        for color, label in items:
            sw = tk.Canvas(self.legend, width=S(10), height=S(10), bg=VOID, highlightthickness=0)
            if color:
                sw.create_rectangle(0, 0, S(10), S(10), fill=color, width=0)
            else:
                sw.create_rectangle(S(4), S(4), S(4) + max(2, S(2)), S(4) + max(2, S(2)), fill=DIM, width=0)
            sw.pack(side="left", padx=(0, S(5)))
            tk.Label(self.legend, text=label, bg=VOID, fg=MUTED, font=self.f["small"]).pack(side="left", padx=(0, S(14)))

    def _cell_at(self, x, y):
        W, H = self.map.winfo_width(), self.map.winfo_height()
        col = int(x / (W / self.MAP_COLS))
        row = int(y / (H / self.MAP_ROWS))
        i = row * self.MAP_COLS + col
        if 0 <= col < self.MAP_COLS and 0 <= row < self.MAP_ROWS and i < len(self.cell_owner):
            return self.cell_owner[i]
        return None

    def _map_motion(self, e):
        self._set_hover(self._cell_at(e.x, e.y))

    def _set_hover(self, key):
        if key == self.hover_key:
            return
        self.hover_key = key
        if key == "__shared":
            used = self.mem["used"] - sum(g["mem"] for g in self.procs)
            self.hover_lbl.configure(text=f"Shared libraries, kernel and drivers  {max(0, used) / core.MB:,.0f} MB")
        elif key:
            g = self._group(key)
            self.hover_lbl.configure(text=f"{g['name']}  {g['mem'] / core.MB:,.0f} MB" if g else "")
        else:
            self.hover_lbl.configure(text="")
        self.draw_map()

    def _map_click(self, e):
        key = self._cell_at(e.x, e.y)
        if not key or key == "__shared":
            return
        iid = self._iid(key)
        if not self.tree.exists(iid):  # hidden by a filter: show everything again
            self.search.delete(0, "end")
            self.search.event_generate("<FocusOut>")
            self.set_view("all")
            self.hide_system = False
            self.hide_switch.set(False)
            self.refresh_table()
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)

    # --------------------------------------------------------------- table ---

    @staticmethod
    def _iid(key):
        return "p" + hashlib.md5(key.encode()).hexdigest()[:12]

    def _group(self, key):
        for g in self.procs:
            if g["key"] == key:
                return g
        return None

    def set_view(self, view):
        self.view = view
        if self.view_seg.get() != view:
            self.view_seg.set(view)
        self.refresh_table()

    def toggle_hide_system(self, on):
        self.hide_system = on
        self.hide_lbl.configure(fg=TEXT if on else MUTED)
        self.refresh_table()

    def sort_by(self, col):
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col, self.sort_desc = col, col in ("mem", "count", "auto")
        self._update_headings()
        self.refresh_table()

    def _update_headings(self):
        for c, text in self.headings.items():
            arrow = (" ▾" if self.sort_desc else " ▴") if c == self.sort_col else ""
            self.tree.heading(c, text=text + arrow)

    def _visible_rows(self):
        if not hasattr(self, "tree"):
            return []
        q = self._search_text()
        min_b = self.cfg.get("min_mb", 10) * core.MB
        rows = []
        for g in self.procs:
            v = self.verdicts.get(g["key"])
            cat = v["category"] if v else None
            if g["mem"] < min_b and g["key"] != self.selected:
                continue
            if q and q not in g["name"].lower():
                continue
            if self.view == "look" and cat not in ("bloatware", "optional", "unknown"):
                continue
            if self.hide_system and cat == "system":
                continue
            rows.append(g)
        order = list(core.CATEGORIES)
        keyfn = {
            "name": lambda g: g["name"].lower(),
            "mem": lambda g: g["mem"],
            "count": lambda g: (g["count"], g["mem"]),
            "auto": lambda g: (any(e["enabled"] for e in self.startup_by_key.get(g["key"], [])), g["mem"]),
            "verdict": lambda g: (order.index(self.verdicts[g["key"]]["category"])
                                  if g["key"] in self.verdicts else len(order), -g["mem"]),
        }[self.sort_col]
        rows.sort(key=keyfn, reverse=self.sort_desc)
        return rows

    def refresh_table(self):
        if not hasattr(self, "tree"):
            return
        rows = self._visible_rows()
        existing = set(self.tree.get_children())
        wanted = set()
        for pos, g in enumerate(rows):
            iid = self._iid(g["key"])
            self.iid_to_key[iid] = g["key"]
            wanted.add(iid)
            v = self.verdicts.get(g["key"])
            if v:
                verdict = core.CATEGORIES[v["category"]]
            elif self.verdicts and g["key"] not in self.analyzed_keys:
                verdict = "Not assessed"
            else:
                verdict = ""
            entries = self.startup_by_key.get(g["key"], [])
            auto = "On" if any(e["enabled"] for e in entries) else ("Off" if entries else "")
            values = (g["name"], f"{g['mem'] / core.MB:,.0f} MB", g["count"], auto, verdict)
            tags = (v["category"],) if v else ()
            if iid in existing:
                self.tree.item(iid, values=values, tags=tags)
                if self.tree.index(iid) != pos:
                    self.tree.move(iid, "", pos)
            else:
                self.tree.insert("", pos, iid=iid, values=values, tags=tags)
        for iid in existing - wanted:
            self.tree.delete(iid)
        if self.view == "look" and not self.verdicts:
            self.set_status("Worth a look needs an analysis first. Click Analyze with AI.")

    def clear_selection(self):
        if self.tree.selection():
            self.tree.selection_remove(*self.tree.selection())
        else:
            self.selected = None
            self.render_detail()
            self.draw_map()

    def _on_select(self, _e=None):
        sel = self.tree.selection()
        self.selected = self.iid_to_key.get(sel[0]) if sel else None
        self.render_detail()
        self.draw_map()

    # -------------------------------------------------------------- detail ---

    def render_detail(self, force=False):
        g = self._group(self.selected) if self.selected else None
        v = self.verdicts.get(g["key"]) if g else None
        # Only rebuild when something visible changed, so the panel doesn't jump every refresh
        entries = self.startup_by_key.get(g["key"], []) if g else []
        chat = self.chats.get(g["key"], []) if g else []
        sig = (len(chat), g["key"] in self.chat_pending if g else None,
               self.selected, id(v), v.get("category") if v else None, self.summary, self.analyzed_at,
               f"{g['mem'] / core.MB:,.0f}|{g['count']}|{g['exe']}" if g else None,
               tuple((e["id"], e["enabled"]) for e in entries), self.startup_scanned,
               g["key"] in self.cfg["keep"] if g else None)
        if sig == getattr(self, "_detail_sig", None) and not force:
            return
        old_sig = getattr(self, "_detail_sig", None)
        keep_scroll = bool(old_sig) and old_sig[2] == self.selected
        old_pos = self._detail_canvas.yview()[0] if keep_scroll and hasattr(self, "_detail_canvas") else 0
        # keep a half-typed question and the cursor when the panel is rebuilt
        typed, had_focus = "", False
        entry = getattr(self, "chat_entry", None)
        if entry is not None and keep_scroll:
            try:
                typed = "" if getattr(entry, "is_placeholder", False) else entry.get()
                had_focus = is_focused(entry)
            except tk.TclError:
                pass
        self.chat_entry = None
        self._detail_sig = sig

        d = self.detail
        for w in d.winfo_children():
            w.destroy()
        pad = {"padx": S(18)}
        wrap = S(300)
        # thin bar on the left in the verdict's colour, so the verdict reads at a glance
        accent_color = CAT_COLORS[v["category"]][0] if v else LINE
        accent = tk.Frame(d, bg=PANEL, width=S(3))
        accent.pack(side="left", fill="y")
        tween(accent, "in", 300, lambda t: accent.configure(bg=mix(PANEL, accent_color, t)))

        if g:  # actions first, packed to the bottom, so long texts can never push them out of view
            acts = tk.Frame(d, bg=PANEL)
            acts.pack(side="bottom", fill="x", pady=(S(8), S(16)), **pad)
            acts.columnconfigure((0, 1), weight=1, uniform="a")
            any_on = any(e["enabled"] for e in entries)
            kept = g["key"] in self.cfg["keep"]
            buttons = [
                ("Open file location", lambda: self.open_location(g), bool(g["exe"]), "ghost"),
                ("Search the web", lambda: self.search_web(g), not g["protected"], "ghost"),
                ("Turn off autostart" if any_on or not entries else "Turn on autostart",
                 lambda: self.toggle_autostart(g), bool(entries), "ghost"),
                ("Installed apps", lambda: self.open_settings_uri("ms-settings:appsfeatures"), os.name == "nt", "ghost"),
                ("Remove mark" if kept else "Mark as needed", lambda: self.toggle_keep(g),
                 not g["protected"] and g["key"] not in core.CRITICAL, "ghost"),
                ("End process", lambda: self.end_process(g), core.can_end(g, v) and not kept, "danger"),
            ]
            for i, (text, cmd, enabled, kind) in enumerate(buttons):
                b = FlatButton(acts, text, cmd, kind, self.f["button"], padx=10, pady=6)
                b.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0, S(4)) if i % 2 == 0 else 0,
                       pady=(0, S(4)))
                b.set_enabled(enabled)

        # scrollable text area
        canvas = tk.Canvas(d, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(d, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=PANEL)
        canvas.create_window(0, 0, window=body, anchor="nw")
        self._detail_canvas = canvas

        def relayout(_e=None):
            canvas.configure(scrollregion=(0, 0, body.winfo_reqwidth(), body.winfo_reqheight()))
            if body.winfo_reqheight() > canvas.winfo_height() > 1:
                if not sb.winfo_ismapped():
                    sb.pack(side="right", fill="y", before=canvas)
            elif sb.winfo_ismapped():
                sb.pack_forget()
                canvas.yview_moveto(0)
        body.bind("<Configure>", relayout)
        canvas.bind("<Configure>", relayout)

        def wheel(up):
            if sb.winfo_ismapped():
                canvas.yview_scroll(-2 if up else 2, "units")
        canvas._on_wheel = wheel

        def text(t, font="body", fg=TEXT, top=0):
            tk.Label(body, text=t, bg=PANEL, fg=fg, font=self.f[font], justify="left",
                     wraplength=wrap).pack(anchor="w", pady=(top, 0), **pad)

        def heading(t):
            text(t, "small", DIM, S(14))

        if not g:
            if self.verdicts:
                text("Summary", "title", top=S(18))
                text(self.summary, top=S(8))
                saved = core.savings(self.procs, self.verdicts) / core.MB
                text(f"Closing everything marked bloatware or optional would free about {saved:,.0f} MB.",
                     fg=MUTED, top=S(12))
                text(f"Assessed by {self.model} at {self.analyzed_at:%H:%M}. Pick a program to see its verdict.",
                     "small", DIM, S(12))
                FlatButton(body, "Export report", self.export, "ghost", self.f["button"]).pack(
                    anchor="w", pady=(S(16), 0), **pad)
            else:
                text("Nothing selected", "title", top=S(18))
                text("Pick a program in the list or click a block in the memory map.\n\n"
                     "Analyze with AI gives every program a verdict and tells you what to do about it. "
                     "Nothing gets closed unless you click End process yourself.", fg=MUTED, top=S(8))
            return

        top_row = tk.Frame(body, bg=PANEL)
        top_row.pack(fill="x", padx=(S(10), S(8)), pady=(S(8), 0))
        ask = FlatButton(top_row, "Ask the AI", self._jump_to_chat, "quiet", self.f["small"], padx=8, pady=3)
        ask.fg_normal = CYAN
        ask._paint()
        ask.pack(side="left")
        FlatButton(top_row, "Back to summary" if self.verdicts else "Close", self.clear_selection, "quiet",
                   self.f["small"], padx=8, pady=3).pack(side="right")
        text(g["name"], "title", top=S(2))
        info = winsys.file_info(g["exe"])
        if info:
            text(", ".join(x for x in (info.get("company"), info.get("description") or info.get("product")) if x),
                 fg=MUTED, top=S(2))
        inst = f"{g['count']} process{'es' if g['count'] != 1 else ''}"
        text(f"{g['mem'] / core.MB:,.0f} MB in {inst}", fg=MUTED, top=S(2))
        if v:
            cat = v["category"]
            chip_row = tk.Frame(body, bg=PANEL)
            chip_row.pack(anchor="w", pady=(S(12), 0), **pad)
            tk.Label(chip_row, text=core.CATEGORIES[cat], bg=CAT_COLORS[cat][0],
                     fg=VOID if cat != "system" else TEXT, font=self.f["strong"],
                     padx=S(8), pady=S(2)).pack(side="left")
            conf = v.get("confidence", "medium")
            text(f"{core.CATEGORY_HINT[cat]}. {conf.capitalize()} confidence.", "small", MUTED, S(4))
            if v.get("what_is_it"):
                heading("What it is")
                text(v["what_is_it"], top=S(2))
            if v.get("recommendation"):
                heading("What to do")
                text(v["recommendation"], top=S(2))
            if v.get("adjusted"):
                heading("Corrected")
                text(v["adjusted"], fg="#ffc857" if v.get("suspicious") else MUTED, top=S(2))
            elif v.get("checked") and cat in ("bloatware", "optional"):
                heading("Double-checked")
                text(v["checked"], fg=MUTED, top=S(2))
            if v.get("setup_match"):
                heading("Based on your setup")
                text(f"\u201c{v['setup_match']}\u201d", fg=MUTED, top=S(2))
        elif self.verdicts:
            text("Not part of the last analysis. It was too small or started later. "
                 "Analyze again to include it.", fg=MUTED, top=S(12))
        if self.startup_scanned and os.name == "nt" or entries:
            heading("Starts with Windows")
            if entries:
                for e in entries:
                    state = ("on" if e["enabled"] else "off") if e["kind"] != "service" else \
                            ("starts automatically" if e["enabled"] else "set to manual")
                    text(f"{e['label']}, {state}", top=S(2))
            else:
                text("No autostart entry found. If it keeps coming back, another program or a "
                     "scheduled task starts it.", fg=MUTED, top=S(2))
        grow = self.growing.get(g["key"])
        if grow:
            heading("Keeps growing")
            text(f"From {grow['from'] / core.GB:.1f} to {grow['to'] / core.GB:.1f} GB in {grow['minutes']:.0f} "
                 "minutes. That can be a memory leak, restarting the program usually fixes it.", fg="#ffc857", top=S(2))
        heading("Location")
        text(g["exe"] or ("Hidden. Run as admin to see it." if g["protected"] else "Not readable"),
             "small", MUTED, S(2))

        # ask the AI about this program
        tk.Frame(body, bg=LINE, height=1).pack(fill="x", padx=S(18), pady=(S(18), S(4)))
        text("Ask the AI about it", "strong", TEXT, S(8))
        for q, a in chat:
            text(q, "small", CYAN, S(10))
            text(a, top=S(3))
        pending = self.chat_pending.get(g["key"])
        if pending:
            text(pending, "small", CYAN, S(10))
            text("Thinking ...", fg=MUTED, top=S(3))
        elif not chat:
            chips = tk.Frame(body, bg=PANEL)
            chips.pack(anchor="w", padx=S(18), pady=(S(6), 0), fill="x")
            for question in ("Is it safe to close?", "Do I need this?", "How do I remove it for good?"):
                FlatButton(chips, question, lambda q=question: self.ask_ai(g, q), "ghost", self.f["small"],
                           padx=8, pady=3, anchor="w").pack(anchor="w", pady=(0, S(4)))
        row = tk.Frame(body, bg=PANEL)
        row.pack(fill="x", padx=S(18), pady=(S(10), 0))
        entry = styled_entry(row, self.f["body"], width=20)
        entry.pack(side="left", fill="x", expand=True)
        self._placeholder(entry, "Ask anything ..." if not chat else "Ask a follow-up ...")
        if typed:
            entry.delete(0, "end")
            entry.configure(fg=TEXT)
            entry.is_placeholder = False
            entry.insert(0, typed)
        send = FlatButton(row, "Ask", lambda: self._send_question(g), "ghost", self.f["button"], padx=12)
        send.pack(side="left", padx=(S(6), 0), fill="y")
        send.set_enabled(not pending)
        entry.bind("<Return>", lambda e: self._send_question(g))
        self.chat_entry = entry
        text(self._ask_cost_hint(), "small", DIM, S(6))
        tk.Frame(body, bg=PANEL, height=S(12)).pack()
        if had_focus:
            self.root.after(10, lambda: (entry.focus_set(), entry.icursor("end")))
        if getattr(self, "_scroll_chat", False):
            self._scroll_chat = False
            self.root.after(60, lambda: canvas.yview_moveto(1.0))
        elif old_pos:
            self.root.after(20, lambda: canvas.yview_moveto(old_pos))

    def show_welcome(self):
        WelcomeDialog(self)

    # ------------------------------------------------------ ask about one ---

    def _jump_to_chat(self):
        if hasattr(self, "_detail_canvas"):
            self._detail_canvas.yview_moveto(1.0)
        if self.chat_entry is not None:
            self.chat_entry.focus_set()

    def _ask_cost_hint(self):
        p, model = self.cfg["provider"], core.model_for(self.cfg)
        if core.PROVIDERS[p]["where"] == "local":
            return f"Answered by {model} on your PC, free."
        price = core.price_for(p, model, getattr(self, "prices", {}))
        cost = core.format_usd(*core.cost_range(900, 250, price, model)) if price else "a tiny amount"
        return f"Answered by {model}, costs {cost} per question."

    def _send_question(self, g):
        e = self.chat_entry
        if e is None or getattr(e, "is_placeholder", False):
            return
        question = e.get().strip()
        if question:
            self.ask_ai(g, question)

    def ask_ai(self, g, question):
        key = g["key"]
        if key in self.chat_pending:
            return
        cfg = dict(self.cfg)
        api_key, _ = core.resolve_api_key(cfg)
        if core.needs_key(cfg["provider"]) and not api_key:
            self.show_page("settings")
            self.settings_msg.configure(text="Add an API key first, or let the AI run on this PC.", fg="#ffc857")
            return
        self.chat_pending[key] = question
        self._scroll_chat = True
        self.chat_entry = None  # the question is sent, don't carry the text over
        self.render_detail(force=True)
        self.start_loading()
        history = list(self.chats.get(key, []))
        verdict = self.verdicts.get(key)
        autostart = [x["label"] for x in self.startup_by_key.get(key, []) if x["enabled"]]

        def work():
            try:
                answer = core.ask_about(cfg, api_key, g, verdict, question, history, autostart)
            except core.AIError as err:
                answer = f"Couldn't get an answer: {err}"
            except Exception as err:
                answer = f"Something went wrong: {err}"
            self.q.put(("answer", key, question, answer))
        threading.Thread(target=work, daemon=True).start()

    def _got_answer(self, key, question, answer):
        self.stop_loading()
        self.chat_pending.pop(key, None)
        self.chats.setdefault(key, []).append((question, answer))
        self._scroll_chat = True
        self.render_detail(force=True)

    # --------------------------------------------------------- right click ---

    def _menu(self):
        return tk.Menu(self.root, tearoff=0, bg=PANEL, fg=TEXT, activebackground=SELECT, activeforeground=TEXT,
                       disabledforeground=DIM, bd=0, relief="flat", font=self.f["body"])

    def _program_menu(self, e):
        iid = self.tree.identify_row(e.y) if e.y else (self.tree.selection() or [None])[0]
        if not iid:
            return
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        g = self._group(self.iid_to_key.get(iid))
        if not g:
            return
        v = self.verdicts.get(g["key"])
        entries = self.startup_by_key.get(g["key"], [])
        kept = g["key"] in self.cfg["keep"]
        m = self._menu()
        state = lambda ok: "normal" if ok else "disabled"
        m.add_command(label="Open file location", command=lambda: self.open_location(g), state=state(g["exe"]))
        m.add_command(label="Search the web", command=lambda: self.search_web(g), state=state(not g["protected"]))
        m.add_separator()
        if entries:
            on = any(x["enabled"] for x in entries)
            m.add_command(label="Turn off autostart" if on else "Turn on autostart",
                          command=lambda: self.toggle_autostart(g))
        m.add_command(label="Remove needed mark" if kept else "Mark as needed", command=lambda: self.toggle_keep(g),
                      state=state(not g["protected"] and g["key"] not in core.CRITICAL))
        m.add_separator()
        m.add_command(label="End process ...", command=lambda: self.end_process(g),
                      state=state(core.can_end(g, v) and not kept))
        m.tk_popup(e.x_root, e.y_root)

    def _startup_menu(self, e):
        iid = self.stree.identify_row(e.y)
        if not iid:
            return
        if iid not in self.stree.selection():
            self.stree.selection_set(iid)
        self._startup_buttons()
        sel = self._selected_entries()
        m = self._menu()
        m.add_command(label="Turn off", command=lambda: self._startup_selected(False),
                      state="normal" if any(x["enabled"] for x in sel) else "disabled")
        m.add_command(label="Turn on", command=lambda: self._startup_selected(True),
                      state="normal" if any(not x["enabled"] for x in sel) else "disabled")
        if len(sel) == 1 and sel[0].get("exe"):
            exe = sel[0]["exe"]
            m.add_separator()
            m.add_command(label="Open file location", command=lambda: self.open_location({"exe": exe}))
            m.add_command(label="Search the web", command=lambda: self.search_web({"name": os.path.basename(exe)}))
        m.tk_popup(e.x_root, e.y_root)

    # -------------------------------------------------- startup + clean up ---

    def rescan_startup(self):
        threading.Thread(target=lambda: self.q.put(("startup", winsys.startup_entries())), daemon=True).start()

    def _remap_startup(self):
        self.startup_by_key = winsys.match_entries(self.startup_entries, self.procs)
        self.entry_to_key = {e["id"]: k for k, es in self.startup_by_key.items() for e in es}
        self._update_cleanup_button()

    def _candidates(self):
        return core.cleanup_candidates(self.procs, self.verdicts, self.startup_by_key, self.cfg["keep"])

    def _update_cleanup_button(self):
        if not hasattr(self, "cleanup_btn"):
            return
        n = len(self._candidates()) if self.verdicts else 0
        self.cleanup_btn.configure(text=f"Clean up ({n})" if n else "Clean up")
        self.cleanup_btn.set_enabled(n > 0 and not self.busy)

    def open_cleanup(self):
        cands = self._candidates()
        if not cands:
            return
        windows = winsys.visible_window_pids()
        for c in cands:
            c["group"]["window"] = any(pid in windows for pid in c["group"]["pids"])
            if c["group"]["window"]:
                c["selected"] = False
        self.cleanup_dialog = CleanupDialog(self, cands)

    def toggle_autostart(self, g):
        entries = self.startup_by_key.get(g["key"], [])
        if not entries:
            return
        turn_on = not any(e["enabled"] for e in entries)
        self._set_entries(entries, turn_on)

    def _set_entries(self, entries, enabled):
        def work():
            problems, done = [], 0
            for e in entries:
                try:
                    ok, msg = winsys.set_startup_enabled(e, enabled)
                except Exception as ex:
                    ok, msg = False, f"{e['name']}: {ex}"
                done += ok
                if not ok:
                    problems.append(msg)
            word = "on" if enabled else "off"
            text = problems[0] if problems else f"Turned {word} {done} autostart entr{'y' if done == 1 else 'ies'}."
            self.q.put(("startup_changed", not problems, text))
        threading.Thread(target=work, daemon=True).start()

    def toggle_keep(self, g):
        keep = self.cfg["keep"]
        v = self.verdicts.get(g["key"])
        if g["key"] in keep:
            keep.remove(g["key"])
            if v and "_before" in v:
                before = v.pop("_before")
                v.clear()
                v.update(before)
        else:
            keep.append(g["key"])
            if v:
                v["_before"] = {k: val for k, val in v.items() if k != "_before"}
                core.apply_rules(self.verdicts, [g], keep)
        core.save_config(self.cfg)
        self._update_keep_label()
        self.refresh_table()
        self.draw_map()
        self.render_detail(force=True)
        self._update_cleanup_button()

    # ------------------------------------------------------------- actions ---

    # ------------------------------------------------------------ updates ---

    def _show_update(self):
        """The 'new version' link in the status bar leads to the update controls in Settings."""
        self.show_page("settings")
        if hasattr(self, "update_msg") and getattr(self, "update_info", None):
            self._update_checked(self.update_info)
            outer = self.pages["settings"].winfo_children()[0]
            canvas = outer.winfo_children()[0] if outer.winfo_children() else None
            if isinstance(canvas, tk.Canvas):
                self.root.after(50, lambda: canvas.yview_moveto(1.0))

    def check_updates_now(self):
        self.check_btn.set_enabled(False)
        self.update_action.pack_forget()
        fade_label(self.update_msg, "Checking GitHub ...", MUTED, VOID)
        self.start_loading()
        threading.Thread(target=lambda: self.q.put(("update_checked", core.update_status())), daemon=True).start()

    def _update_checked(self, st):
        self.stop_loading()
        self.check_btn.set_enabled(True)
        self.update_info = st
        if st["state"] == "error":
            fade_label(self.update_msg, st["error"], "#ffc857", VOID)
        elif st["state"] == "current":
            fade_label(self.update_msg, f"You have the newest version, RAMCheck {core.VERSION}.", MUTED, VOID)
        else:
            installed = core.install_mode() == "installed"
            fade_label(self.update_msg, f"RAMCheck {st['version']} is available (you have {core.VERSION}). " +
                       ("It's downloaded from GitHub, checked against the release's checksum and installed over "
                        "this version. Your settings stay." if installed else
                        "Download the new version from the release page."), CYAN, VOID)
            self.update_action.configure(text="Download and install" if installed else "Open release page")
            self.update_action.pack(side="left", padx=(S(8), 0))
            self.update_lbl.configure(text=f"RAMCheck {st['version']} is available")

    def _update_action(self):
        st = getattr(self, "update_info", None) or {}
        if core.install_mode() != "installed":
            webbrowser.open(st.get("url") or core.REPO_URL + "/releases")
            return
        self.update_action.set_enabled(False)
        self.check_btn.set_enabled(False)
        self.start_loading()

        def progress(done, total):
            text = (f"Downloading ... {done / total * 100:.0f} % of {total / core.MB:.0f} MB" if total
                    else f"Downloading ... {done / core.MB:.0f} MB")
            self.q.put(("update_progress", text))

        def work():
            try:
                self.q.put(("update_ready", core.download_update(progress), None))
            except core.UpdateError as e:
                self.q.put(("update_ready", None, str(e)))
            except Exception as e:
                self.q.put(("update_ready", None, f"Unexpected error: {e}"))
        threading.Thread(target=work, daemon=True).start()

    def _update_ready(self, path, error):
        self.stop_loading()
        self.check_btn.set_enabled(True)
        self.update_action.set_enabled(True)
        if error:
            fade_label(self.update_msg, error, "#ffc857", VOID)
            return
        fade_label(self.update_msg, "Download verified. Starting the installer ...", MUTED, VOID)
        if messagebox.askyesno("Install update", "The new version is downloaded and verified. RAMCheck closes now "
                               "so the installer can update it. Continue?", parent=self.root):
            try:
                core.run_installer(path)
            except OSError as e:
                fade_label(self.update_msg, f"Couldn't start the installer: {e}", "#ffc857", VOID)
                return
            self.close()

    def _open_folder(self, path):
        try:
            os.startfile(path)
        except AttributeError:
            subprocess.Popen(["xdg-open", path])
        except OSError:
            self.set_status(f"Couldn't open {path}", MAGENTA)

    def open_location(self, g):
        if os.name == "nt":
            subprocess.Popen(["explorer", f"/select,{g['exe']}"])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(g["exe"])])

    def search_web(self, g):
        webbrowser.open("https://duckduckgo.com/?q=" + urllib.parse.quote(f"{g['name']} windows process"))

    def open_settings_uri(self, uri):
        try:
            os.startfile(uri)
        except (AttributeError, OSError):
            self.set_status("Couldn't open Windows settings.", MAGENTA)

    def end_process(self, g):
        v = self.verdicts.get(g["key"])
        warn = ""
        if v and v["category"] == "important":
            warn = "\n\nThe AI marked this as important. Things like fan control or audio settings may stop working."
        if not messagebox.askyesno(
                "End process",
                f"Close {g['name']} ({g['count']} process{'es' if g['count'] != 1 else ''})?\n\n"
                f"Unsaved work in it will be lost. If it starts with Windows, it comes back after "
                f"a restart unless you remove it from Startup apps.{warn}",
                icon="warning", parent=self.root):
            return
        self.set_status(f"Closing {g['name']} ...")
        def work():
            try:
                result = core.end_group(g)
            except Exception as e:
                result = (0, [f"unexpected error: {e}"])
            self.q.put(("ended", g["name"], *result))
        threading.Thread(target=work, daemon=True).start()

    def _after_end(self, name, closed, failed):
        if failed:
            self.set_status(f"{name}: closed {closed}, {len(failed)} failed. {failed[0]}", MAGENTA)
        else:
            self.set_status(f"Closed {name}.")
        self.selected = None
        self.refresh()

    def run_as_admin(self):
        if core.relaunch_as_admin():
            self.close()
        elif core.install_mode() == "store":
            messagebox.showinfo("Run as admin", "Close RAMCheck, then right-click it in the Start menu and choose "
                                "More > Run as administrator.", parent=self.root)
        else:
            self.set_status("Windows didn't allow running as admin.", MAGENTA)

    def export(self):
        if not self.verdicts:
            self.set_status("Nothing to export yet. Run Analyze with AI first.", "#ffc857")
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export report", defaultextension=".md",
            initialdir=core.default_report_folder(),
            initialfile=f"ram_report_{dt.datetime.now():%Y-%m-%d_%H-%M}.md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(core.build_markdown(self.summary, self.verdicts, self.procs, self.mem, self.model))
            self.set_status(f"Report saved to {path}")
        except OSError as e:
            self.set_status(f"Couldn't save the report: {e}", MAGENTA)

    # ------------------------------------------------------------ analysis ---

    def analyze(self):
        if self.busy or not self.procs:
            return
        cfg = self.cfg
        key, _ = core.resolve_api_key(cfg)
        if core.needs_key(cfg["provider"]) and not key:
            self.show_page("settings")
            self.settings_msg.configure(text=f"Add a {core.PROVIDERS[cfg['provider']]['name']} API key first, "
                                             "or let it run on this PC.", fg="#ffc857")
            return
        min_b = cfg.get("min_mb", 10) * core.MB
        top = [g for g in self.procs if g["mem"] >= min_b][:cfg.get("top", 40)]
        mem = dict(self.mem)
        self.busy = True
        self.start_loading()
        self.btn_analyze.configure(text="Analyzing ...")
        self.btn_analyze.set_enabled(False)
        self.analysis_started = time.time()
        who = core.model_for(cfg)
        self.progress_text = f"Asking {who}"
        self._analysis_tick(who, len(top))

        startup_by_key = dict(self.startup_by_key) if self.startup_scanned else None

        def work():
            try:
                result = core.analyze(top, mem, cfg, key, startup_by_key=startup_by_key,
                                      progress=lambda t: self.q.put(("progress", t)))
                self.q.put(("analysis", *result, {g["key"] for g in top}))
            except core.AIError as e:
                self.q.put(("ai_error", str(e)))
            except Exception as e:
                self.q.put(("ai_error", f"Unexpected error: {e}"))
        threading.Thread(target=work, daemon=True).start()

    def _analysis_tick(self, who, n):
        if not self.busy:
            return
        secs = int(time.time() - self.analysis_started)
        self.set_status(f"{self.progress_text} ({n} programs) ... {secs} s", CYAN)
        self.root.after(500, lambda: self._analysis_tick(who, n))

    def _done_busy(self):
        self.busy = False
        self.stop_loading()
        self.btn_analyze.configure(text="Analyze again")
        self.btn_analyze.set_enabled(True)

    def _apply_analysis(self, summary, verdicts, model, note, keys):
        self._done_busy()
        self.summary, self.verdicts, self.model = summary, verdicts, model
        self.analysis_note = note
        core.save_last_analysis(summary, verdicts, model, note, keys)
        self.analyzed_keys = keys
        self.analyzed_at = dt.datetime.now()
        secs = int(time.time() - self.analysis_started)
        self.set_status(f"Assessed {len(verdicts)} programs with {model} in {secs} s. {note}".strip())
        saved = core.savings(self.procs, verdicts) / core.MB
        self.savings_lbl.configure(text=f"Possible savings about {saved:,.0f} MB")
        self.refresh_table()
        self.draw_map(reveal=True)
        self.render_detail()
        self._update_cleanup_button()
        self.refresh_startup_table()

    def _analysis_failed(self, message):
        self._done_busy()
        if not self.verdicts:
            self.btn_analyze.configure(text="Analyze with AI")
        self.set_status(message, MAGENTA)
        if "API key" in message or "model" in message.lower():
            if messagebox.askyesno("Analysis failed", f"{message}\n\nOpen Settings now?", parent=self.root):
                self.show_page("settings")

    def close(self):
        if self.test:
            self.test.stop()
        self.stop.set()
        self.refresh_now.set()
        try:  # remember size and position for next time
            zoomed = self.root.state() == "zoomed"
            if zoomed:
                self.root.state("normal")
            self.cfg["window"] = {"geometry": self.root.geometry(), "zoomed": zoomed}
            core.save_config(self.cfg)
        except (tk.TclError, OSError):
            pass
        self.root.destroy()


# -------------------------------------------------------------- welcome ---

class WelcomeDialog:
    """First start: what RAMCheck does, what it never does, and where the AI runs."""

    POINTS = [
        ("See what's using your RAM", "Every program, grouped and measured like in Task Manager, a map of your "
                                      "whole memory, and a test that checks your RAM for errors."),
        ("Nothing happens behind your back", "RAMCheck never closes, changes or uninstalls anything on its own. "
                                             "Every autostart change can be undone, and it doesn't run in the "
                                             "background or start with Windows."),
        ("You choose the AI", "A cloud service with your own API key, or a free model on your PC. Only program "
                              "names, paths, sizes and publishers are sent, never your files."),
        ("Open source", "All of the code is public on GitHub, so anyone can check what it does."),
    ]

    def __init__(self, app):
        self.app = app
        f = app.f
        top = self.top = tk.Toplevel(app.root)
        top.title("Welcome to RAMCheck")
        top.configure(bg=VOID)
        top.transient(app.root)
        w, h = S(560), S(500)
        x = app.root.winfo_rootx() + (app.root.winfo_width() - w) // 2
        y = app.root.winfo_rooty() + max(S(40), (app.root.winfo_height() - h) // 3)
        top.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        top.resizable(False, False)
        dark_title_bar(top)
        top.protocol("WM_DELETE_WINDOW", self.close)
        top.bind("<Escape>", lambda e: self.close())
        body = tk.Frame(top, bg=VOID)
        body.pack(fill="both", expand=True, padx=S(28), pady=S(24))
        head = tk.Frame(body, bg=VOID)
        head.pack(anchor="w")
        logo = tk.Canvas(head, width=S(22), height=S(22), bg=VOID, highlightthickness=0)
        app._draw_logo(logo)
        logo.pack(side="left", padx=(0, S(10)))
        tk.Label(head, text="Welcome to RAMCheck", bg=VOID, fg=TEXT, font=f["title"]).pack(side="left")
        for title, text in self.POINTS:
            row = tk.Frame(body, bg=VOID)
            row.pack(anchor="w", fill="x", pady=(S(16), 0))
            mark = tk.Canvas(row, width=S(8), height=S(8), bg=VOID, highlightthickness=0)
            mark.create_rectangle(0, 0, S(8), S(8), fill=CYAN, width=0)
            mark.pack(side="left", anchor="n", pady=(S(6), 0))
            col = tk.Frame(row, bg=VOID)
            col.pack(side="left", padx=(S(12), 0), fill="x")
            tk.Label(col, text=title, bg=VOID, fg=TEXT, font=f["strong"], anchor="w").pack(anchor="w")
            tk.Label(col, text=text, bg=VOID, fg=MUTED, font=f["body"], justify="left",
                     wraplength=w - S(100), anchor="w").pack(anchor="w", pady=(S(2), 0))
        foot = tk.Frame(body, bg=VOID)
        foot.pack(side="bottom", fill="x")
        FlatButton(foot, "Set up the AI", self.setup, "primary", f["strong"], padx=16).pack(side="right")
        FlatButton(foot, "Look around first", self.close, "ghost", f["button"]).pack(side="right", padx=S(8))
        self._grab()

    def _grab(self, tries=10):
        try:
            self.top.grab_set()
            self.top.focus_set()
        except tk.TclError:
            if tries:
                self.top.after(50, lambda: self._grab(tries - 1))

    def close(self):
        self.app.cfg["welcomed"] = True
        try:
            core.save_config(self.app.cfg)
        except OSError:
            pass
        try:
            self.top.grab_release()
        except tk.TclError:
            pass
        self.top.destroy()

    def setup(self):
        self.close()
        self.app.show_page("settings")


# ------------------------------------------------------------- clean up ---

class CleanupDialog:
    """Pick bloatware to close and to remove from autostart, in one go."""

    def __init__(self, app, candidates):
        self.app, self.cands = app, candidates
        f = app.f
        top = self.top = tk.Toplevel(app.root)
        top.title("Clean up")
        top.configure(bg=VOID)
        top.transient(app.root)
        w = S(640)
        h = min(S(660), app.root.winfo_height() - S(40))
        x = app.root.winfo_rootx() + (app.root.winfo_width() - w) // 2
        y = app.root.winfo_rooty() + S(30)
        top.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        top.minsize(S(520), S(400))
        dark_title_bar(top)
        top.bind("<Escape>", lambda e: self.close())
        top.protocol("WM_DELETE_WINDOW", self.close)

        self.body = tk.Frame(top, bg=VOID)
        self.body.pack(fill="both", expand=True, padx=S(22), pady=S(18))
        b = self.body
        tk.Label(b, text="Clean up", bg=VOID, fg=TEXT, font=f["title"]).pack(anchor="w")
        tk.Label(b, bg=VOID, fg=MUTED, font=f["body"], justify="left", wraplength=w - S(50),
                 text="These were marked as bloatware or optional. Sure bloatware is selected already, "
                      "everything else is up to you. Nothing is uninstalled, and every autostart change "
                      "can be undone on the Startup tab.").pack(anchor="w", pady=(S(4), S(12)))

        # footer first so it always stays visible
        foot = tk.Frame(b, bg=VOID)
        foot.pack(side="bottom", fill="x", pady=(S(12), 0))
        self.go_btn = FlatButton(foot, "Clean up", self.run, "alert", f["strong"], padx=16)
        self.go_btn.pack(side="right")
        self.cancel_btn = FlatButton(foot, "Cancel", self.close, "ghost", f["button"])
        self.cancel_btn.pack(side="right", padx=S(8))
        self.total_lbl = tk.Label(foot, text="", bg=VOID, fg=MUTED, font=f["small"], anchor="w",
                                  justify="left", wraplength=S(330))
        self.total_lbl.pack(side="left", fill="x", expand=True)

        opts = tk.Frame(b, bg=VOID)
        opts.pack(side="bottom", fill="x", pady=(S(12), 0))
        self.opt_close = self._option(opts, "Close them now", True)
        self.opt_auto = self._option(opts, "Stop them from starting with Windows", True)
        needs_admin = any(e["needs_admin"] for c in candidates for e in c["startup"])
        if needs_admin and os.name == "nt" and not core.is_admin():
            note = tk.Frame(opts, bg=VOID)
            note.pack(anchor="w", pady=(S(6), 0))
            tk.Label(note, text="Some of these are services or set up for all users. Windows only lets "
                                "admins change those.", bg=VOID, fg="#ffc857", font=f["small"],
                     wraplength=w - S(200), justify="left").pack(side="left")
            FlatButton(note, "Run as admin", app.run_as_admin, "quiet", f["small"], padx=8, pady=3).pack(side="left", padx=S(6))

        # scrollable list
        box = tk.Frame(b, bg=PANEL)
        box.pack(fill="both", expand=True)
        canvas = tk.Canvas(box, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        rows = tk.Frame(canvas, bg=PANEL)
        win = canvas.create_window(0, 0, window=rows, anchor="nw")
        rows.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))

        canvas._on_wheel = lambda up: canvas.yview_scroll(-2 if up else 2, "units")

        self.checks = []
        for c in candidates:
            self.checks.append(self._row(rows, c))
        self.update_total()
        self._grab()

    def _grab(self, tries=10):
        try:
            self.top.grab_set()
            self.top.focus_set()
        except tk.TclError:  # window not visible yet
            if tries:
                self.top.after(50, lambda: self._grab(tries - 1))

    def _option(self, parent, text, on):
        row = tk.Frame(parent, bg=VOID)
        row.pack(anchor="w", pady=S(3))
        sw = Switch(row, on, lambda _on: self.update_total())
        sw.pack(side="left")
        lbl = tk.Label(row, text=text, bg=VOID, fg=TEXT, font=self.app.f["body"], cursor="hand2")
        lbl.pack(side="left", padx=S(10))
        lbl.bind("<Button-1>", lambda e: sw.toggle())
        return sw

    def _row(self, parent, c):
        f, g, v = self.app.f, c["group"], c["verdict"]
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=S(12), pady=(S(10), 0))
        chk = Check(row, c["selected"], self.update_total)
        chk.grid(row=0, column=0, rowspan=2, sticky="n", pady=(S(3), 0))
        name = tk.Label(row, text=g["name"], bg=PANEL, fg=TEXT, font=f["strong"], cursor="hand2")
        name.grid(row=0, column=1, sticky="w", padx=(S(10), 0))
        name.bind("<Button-1>", lambda e: chk.toggle())
        tk.Label(row, text=f"{g['mem'] / core.MB:,.0f} MB", bg=PANEL, fg=MUTED, font=f["body"]).grid(
            row=0, column=2, sticky="e")
        row.columnconfigure(1, weight=1)
        bits = [f"{core.CATEGORIES[v['category']]}, {v.get('confidence', 'medium')} confidence"]
        if c["startup"]:
            bits.append("starts with Windows" if len(c["startup"]) == 1 or all(e["kind"] != "service" for e in c["startup"])
                        else "service")
            if any(e["kind"] == "service" for e in c["startup"]):
                bits[-1] = "service, starts automatically"
        if g.get("window"):
            bits.append("has an open window, save your work first")
        color = CAT_COLORS[v["category"]][0]
        tk.Label(row, text=", ".join(bits), bg=PANEL, fg=color, font=f["small"]).grid(
            row=1, column=1, columnspan=2, sticky="w", padx=(S(10), 0))
        if v.get("recommendation"):
            tk.Label(row, text=v["recommendation"], bg=PANEL, fg=MUTED, font=f["small"], justify="left",
                     wraplength=S(520)).grid(row=2, column=1, columnspan=2, sticky="w", padx=(S(10), 0), pady=(S(2), S(4)))
        return chk

    def selected(self):
        return [c for c, chk in zip(self.cands, self.checks) if chk.checked]

    def update_total(self):
        sel = self.selected()
        mb = sum(c["group"]["mem"] for c in sel) / core.MB
        n_auto = sum(len(c["startup"]) for c in sel)
        parts = []
        if self.opt_close.on:
            parts.append(f"frees about {mb:,.0f} MB now")
        if self.opt_auto.on and n_auto:
            parts.append(f"turns off {n_auto} autostart entr{'y' if n_auto == 1 else 'ies'}")
        self.total_lbl.configure(text=f"{len(sel)} selected" + (", " + ", ".join(parts) if parts and sel else ""))
        ok = bool(sel) and (self.opt_close.on or (self.opt_auto.on and n_auto))
        self.go_btn.configure(text=f"Clean up {len(sel)} program{'s' if len(sel) != 1 else ''}" if sel else "Clean up")
        self.go_btn.set_enabled(ok)

    def run(self):
        items = self.selected()
        close, auto = self.opt_close.on, self.opt_auto.on
        self.used_before = core.memory_status()["used"]
        self.app.start_loading()
        self.go_btn.set_enabled(False)
        self.cancel_btn.set_enabled(False)
        self.go_btn.configure(text="Cleaning up ...")
        def work():
            try:
                result = core.run_cleanup(items, close, auto)
            except Exception as e:  # never leave the dialog hanging
                result = (0, 0, [f"Unexpected error: {e}"])
            self.app.q.put(("cleanup_done", *result))
        threading.Thread(target=work, daemon=True).start()

    def show_result(self, closed, disabled, problems):
        self.app.stop_loading()
        f = self.app.f
        for w in self.body.winfo_children():
            w.destroy()
        b = self.body
        tk.Label(b, text="Done", bg=VOID, fg=TEXT, font=f["title"]).pack(anchor="w")
        parts = []
        if closed:
            parts.append(f"closed {closed} program{'s' if closed != 1 else ''}")
        if disabled:
            parts.append(f"turned off {disabled} autostart entr{'y' if disabled == 1 else 'ies'}")
        msg = ("RAMCheck " + " and ".join(parts) + ".") if parts else "Nothing was changed."
        tk.Label(b, text=msg, bg=VOID, fg=TEXT, font=f["body"], justify="left",
                 wraplength=S(580)).pack(anchor="w", pady=(S(6), 0))
        self.freed_lbl = tk.Label(b, text="Measuring how much RAM that freed ..." if closed else "",
                                  bg=VOID, fg=MUTED, font=f["body"], justify="left", wraplength=S(580))
        self.freed_lbl.pack(anchor="w", pady=(S(4), 0))
        if closed:
            self.top.after(3000, self._show_freed)  # give Windows a moment to hand the memory back
        unique = list(dict.fromkeys(problems))
        admin = [p for p in unique if "admin" in p.lower() or "access denied" in p.lower()]
        other = [p for p in unique if p not in admin]
        if admin:
            names = sorted({p.split(":")[0] for p in admin})
            box = tk.Frame(b, bg=VOID)
            box.pack(anchor="w", fill="x", pady=(S(14), 0))
            tk.Label(box, text=f"Needs admin rights: {', '.join(names)}. Windows only lets admins stop "
                               "services and change autostart for all users. Run RAMCheck as admin and use "
                               "Clean up again, your analysis is kept.", bg=VOID, fg="#ffc857", font=f["small"],
                     justify="left", wraplength=S(580)).pack(anchor="w")
            if os.name == "nt" and not core.is_admin():
                FlatButton(box, "Run as admin", self.app.run_as_admin, "ghost", f["button"]).pack(anchor="w", pady=(S(8), 0))
        if other:
            tk.Label(b, text="Didn't work:", bg=VOID, fg="#ffc857", font=f["small"]).pack(anchor="w", pady=(S(14), S(2)))
            for p in other[:8]:
                tk.Label(b, text=p, bg=VOID, fg=MUTED, font=f["small"], justify="left",
                         wraplength=S(580)).pack(anchor="w")
        tk.Label(b, text="If a program comes back after closing it, it's usually started by the vendor's main "
                         "app or a scheduled task. Uninstalling it (Installed apps) is the permanent fix.",
                 bg=VOID, fg=DIM, font=f["small"], justify="left", wraplength=S(580)).pack(anchor="w", pady=(S(14), 0))
        FlatButton(b, "Close", self.close, "primary", f["strong"]).pack(anchor="e", side="bottom")
        self.app.set_status(msg)

    def _show_freed(self):
        try:
            after = core.memory_status()["used"]
            freed = (self.used_before - after) / core.GB
            if freed >= 0.05:
                text = (f"RAM in use went from {self.used_before / core.GB:.1f} to {after / core.GB:.1f} GB, "
                        f"about {freed:.1f} GB freed.")
                fade_label(self.freed_lbl, text, CYAN, VOID)
            else:
                fade_label(self.freed_lbl, "No measurable change. The closed programs were small, or other "
                                           "programs grew in the meantime.", MUTED, VOID)
        except tk.TclError:
            pass

    def close(self):
        try:
            self.top.grab_release()
        except tk.TclError:
            pass
        self.top.destroy()
        self.app.cleanup_dialog = None


# ---------------------------------------------------------------- start ---

def main():
    global SCALE
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # sharp text on high-DPI screens
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RAMCheck.App")
        except Exception:
            pass
    if os.name == "nt":
        try:
            import ctypes
            global _MUTEX  # keep the handle alive; lets the installer see that RAMCheck is open
            _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "RAMCheckAppMutex")
        except Exception:
            pass
    _read_motion_setting()
    root = tk.Tk()
    # Stay invisible until everything is built: no white flash, no jumping window.
    root.configure(bg=VOID)
    invisible = os.name == "nt"
    if invisible:
        root.attributes("-alpha", 0.0)  # mapped (so the dark title bar can be set) but not visible
    else:
        root.withdraw()
    SCALE = max(1.0, root.winfo_fpixels("1i") / 96)
    root.title("RAMCheck")
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = min(S(1200), sw - 60), min(S(800), sh - 90)  # also fits small laptop screens
    root.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
    root.minsize(min(S(1140), w), min(S(600), h))
    if ICON_PNG:
        try:
            root.iconphoto(True, tk.PhotoImage(data=ICON_PNG))
        except tk.TclError:
            pass
    core.ensure_setup_file()
    if invisible:
        dark_title_bar(root)
    App(root)
    root.update_idletasks()
    try:  # the packaged exe shows a splash image while it starts, close it now
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass
    if invisible:
        tween(root, "appear", 180, lambda t: root.attributes("-alpha", t))
    else:
        root.deiconify()
    root.mainloop()


def dark_title_bar(root):
    """Windows draws a white title bar by default, which clashes with the dark window."""
    if os.name != "nt":
        return
    try:
        import ctypes
        root.update()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        on = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))
        caption = ctypes.c_int(0x001C0A0C)  # VOID as 0x00BBGGRR, Windows 11 only
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))
    except Exception:
        pass


if __name__ == "__main__":
    main()
