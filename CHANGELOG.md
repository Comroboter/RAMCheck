# Changelog

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
