# RAMCheck privacy policy

Last updated: 2026-09-30

RAMCheck is a free, open source Windows app made by an individual developer (GitHub: Comroboter). This page explains what data RAMCheck handles. The short version: RAMCheck has no servers, no accounts and no analytics. The developer never receives any of your data.

## What stays on your PC

- Settings, your setup notes, the list of programs you marked as needed, the last analysis, cached price data and error logs are stored in `%APPDATA%\RAMCheck` on your PC.
- API keys you enter are stored there too, encrypted with Windows' own data protection (DPAPI), so only your Windows account on your PC can read them.
- The RAM test only writes test patterns into memory and never reads your files.

## What is sent, and to whom

RAMCheck only connects to the internet for these purposes:

1. **The AI service you choose, when you start an analysis or ask a question.** RAMCheck sends: names of running programs, how much memory they use, their file paths (with your Windows user name removed), publisher and description from the program files, whether a program has a window, is a service or starts with Windows, and the setup notes you wrote. It never sends files, documents, browsing data or personal information. The service you picked (for example Anthropic, OpenAI, Google, OpenRouter or Mistral) processes this under its own privacy policy. With Ollama or LM Studio, the AI runs on your PC and nothing leaves it.
2. **GitHub, to check for updates** (not in the Microsoft Store version). RAMCheck reads the public release page of its repository. No data about you or your PC is sent. You can switch this off in Settings.
3. **OpenRouter's public model list, for cost estimates.** RAMCheck downloads a public price list about once a week. No data about you or your PC is sent.

## Children

RAMCheck is a general utility and doesn't knowingly collect data from anyone, including children.

## Changes and contact

Changes to this policy are published in this file on GitHub. Questions: open an issue at https://github.com/Comroboter/RAMCheck/issues
