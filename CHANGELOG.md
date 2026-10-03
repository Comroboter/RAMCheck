# Changelog

## 1.6

- **Fixed the stutter and drawing glitches at start for good.** The cause: measuring each program's memory locked up Ramwise for a moment per program, so the window couldn't redraw. Ramwise now reads the memory of all programs in a single Windows call, the same way Task Manager does. Much faster, and the numbers now match Task Manager's "Memory" column exactly
- Programs Windows protects (like "Secure System") now show their real name
- The window appears fully drawn instead of fading in, and measuring only starts once it's on screen
- The title bar shows Ramwise's icon again instead of a feather

## 1.5.2

- **Fixed: updates from inside the app could fail without a word.** Ramwise used a hidden helper to start the installer, which security software tends to block. Now the installer is started directly and waits by itself until Ramwise has closed
- If an update still doesn't arrive, Ramwise says so on the next start and offers the download page, details are written to `update.log`
- After a successful update the status bar confirms the new version

## 1.5.1

- Clearer colours in the memory map after an analysis: what needs attention (bloatware, optional, unclear) is warm and bright, everything that's fine is a calm blue family. Neighbouring blocks are told apart by a subtle shade instead of a checkerboard
- Updates are only offered once their files are ready on GitHub. Right after a release, the update window no longer shows up too early and fails

## 1.5

- **Smoother start:** services are read straight from the registry instead of asking Windows about each one, background work starts only after the window is fully there, and the start screen stays until the window has faded in. No more stutter right after starting
- While the first measurement runs, a soft light sweeps over the memory map instead of a frozen screen
- The memory map always spans the full width, its cells stay square. Before an analysis it uses a calmer colour, so the verdict colours stand out once they arrive
- **Memory tab redesigned** as a tidy grid of panels: your RAM next to where your memory goes, the RAM test across the full width, Windows' own test next to growing programs. New "Available" figure
- RAM modules: the maker is read from the part number when Windows only says "Unknown", and identical slot names get their channel added
- Before an analysis, the details panel shows three short steps and an Analyze button instead of "Nothing selected"

## 1.4

- **Update window:** when a new version is out, Ramwise shows what's new right away and installs it with one click. "Don't remind me about this version" skips a version. Security updates are always shown and highlighted
- **Smoother updates:** Ramwise now closes completely before the installer starts, then the update runs with just a progress bar and Ramwise starts again by itself. No more two windows at once
- Start menu and desktop shortcuts carry Ramwise's app ID, so a pinned taskbar icon and the open window stay one icon

## 1.3.1

- The memory map shows how much RAM one square stands for (for example "1 cell = 61 MB"). The value adapts when the window is resized
- The RAM test shows the same for its rows

## 1.3

- **RAMCheck is now Ramwise**, the RAM analyzer & memory test. Same app, a name that sticks
  - Settings, setup notes and API keys move over automatically
  - The installer updates an existing RAMCheck installation in place and removes its old shortcuts
  - The update button in RAMCheck 1.2.x keeps working and installs Ramwise
- Microsoft Store packaging removed, Ramwise is distributed through GitHub only

## 1.2.1

- Scrolling through Settings no longer changes sliders or dropdowns by accident. Sliders now react to clicking, dragging and the arrow keys only
- The memory map and the RAM test keep square cells when the window is resized or maximized. Wider windows show more cells instead of stretched ones
- Boxes in the Memory tab keep their size on large windows

## 1.2

- **Check for updates** button in Settings. The installed version downloads the new installer, verifies it against the release checksum and updates itself
- The "new version" hint in the status bar now leads straight to the update button
- Running the installer again offers **update, repair or uninstall** when RAMCheck is already installed

## 1.1

- New **Memory** tab
  - Your RAM modules: slot, size, type, speed, maker, part number
  - Warns when RAM runs below its rated speed (XMP/EXPO off), in single channel or with mixed kits
  - Where your memory goes: committed memory, page file, kernel memory, hardware reserved
  - RAM error test inside Windows with pattern, random data, address and bit fade tests
  - Schedule Windows Memory Diagnostic and see the result of its last run
  - Spots programs whose memory keeps growing (possible leaks)
- Dark start screen instead of a white window, no more jumping window on start
- Download names without version number, so links always point to the newest release
- Microsoft Store package support
- Version number now only lives in `core.py`

## 1.0

First public release.

- Memory map, live usage graph and a grouped program list
- AI verdict for every program with explanation, confidence and advice
- Ask the AI follow-up questions about any single program
- Clean up: close bloatware and turn off its autostart in one go, with a before/after RAM reading
- Startup tab for startup apps and third-party services, reversible
- Presets with time and cost estimates for the chosen model
- Claude, OpenAI, Gemini, OpenRouter, Mistral, any OpenAI-compatible API, Ollama and LM Studio
- Safety rules that protect Windows components and the AI engine RAMCheck is using
- API keys encrypted with Windows DPAPI
- Installer, portable version and terminal version
