# Changelog

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
