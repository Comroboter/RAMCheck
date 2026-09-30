# Publishing RAMCheck in the Microsoft Store

Everything that could be prepared in advance is in this repository:

| What | Where |
|---|---|
| Store package manifest | `packaging/msix/AppxManifest.xml` |
| Tile and Store icons (all required sizes) | `packaging/msix/Assets/` |
| Script that builds the Store package | `packaging/msix/build_msix.ps1` |
| Automatic Store package on every release | `.github/workflows/release.yml` (needs three repository variables, step 4) |
| Privacy policy (required) | `PRIVACY.md` |
| Listing texts, English and German | below |

The Store version is an MSIX package. Microsoft signs it during certification, so no paid code signing certificate is needed.

## 1. Developer account (free)

1. Go to https://storedeveloper.microsoft.com and click **Get started for free**
2. Choose **Individual developer** and sign in with your Microsoft account
3. Verify your identity with a government ID and a selfie
4. Open **Partner Center**

The account is a contract with Microsoft. If you are under 18, an adult (for example a parent) has to create and own it.

## 2. Reserve the name

Partner Center > **Apps and games** > **New product** > **MSIX or PWA app**. Enter `RAMCheck`. If it's taken, use something like `RAMCheck - RAM Analyzer`.

## 3. Copy the product identity

Your app > **Product management** > **Product identity**. You need three values:

- `Package/Identity/Name` (looks like `12345Comroboter.RAMCheck`)
- `Package/Identity/Publisher` (looks like `CN=1A2B3C4D-...`)
- `Package/Properties/PublisherDisplayName`

## 4. Build the Store package

**Option A, automatic (recommended):** GitHub repository > **Settings** > **Secrets and variables** > **Actions** > tab **Variables** > **New repository variable**, three times:

| Name | Value |
|---|---|
| `STORE_IDENTITY_NAME` | Package/Identity/Name |
| `STORE_PUBLISHER` | Package/Identity/Publisher |
| `STORE_PUBLISHER_DISPLAY_NAME` | Package/Properties/PublisherDisplayName |

From now on every release also builds `RAMCheck-Store.msix`. Get it from **Actions** > the latest "Build release" run > **Artifacts** (it isn't attached to the release, because only the Store can install it). You can also start a build any time with **Actions** > **Build release** > **Run workflow**.

**Option B, on your PC:** install the Windows SDK (`winget install Microsoft.WindowsSDK.10.0.26100`, or from https://developer.microsoft.com/windows/downloads/windows-sdk), then in PowerShell in the RAMCheck folder:

```
.\packaging\msix\build_msix.ps1 -IdentityName "..." -Publisher "CN=..." -PublisherDisplayName "..."
```

The package ends up in `dist\RAMCheck-Store.msix`.

**Optional local test:** add `-TestSign`, then run the printed `Import-Certificate` command once in an admin PowerShell and double-click `dist\RAMCheck-Store-TestSigned.msix`. Uninstall it again before installing the Store version.

## 5. Fill in the submission

Your app > **Start submission**.

**Pricing and availability:** Free. Markets: all.

**Properties:**
- Category: *Utilities & tools*
- Privacy policy URL: `https://github.com/Comroboter/RAMCheck/blob/main/PRIVACY.md`
- Website: `https://github.com/Comroboter/RAMCheck`
- Support contact: `https://github.com/Comroboter/RAMCheck/issues`
- Product declarations: tick that the app doesn't need an account; leave the rest unticked

**Age ratings:** answer the questionnaire honestly. RAMCheck has no violence, no user-to-user communication, no purchases, doesn't share location and isn't a web browser. It will end up as suitable for everyone (3+ / PEGI 3).

**Packages:** upload `RAMCheck-Store.msix`. Device families: Windows 10/11 Desktop.

**Store listings:** add English (United States) and German (Germany) and paste the texts below. At least one screenshot is required, 1366 x 768 or larger: take a few of the Programs tab after an analysis, the Memory tab and the Clean up dialog.

**Submission options > Notes for certification:**

```
No account or login is needed. Everything except the AI verdicts works without setup
(memory map, program list, RAM test in the Memory tab, Startup tab).
To test the AI features: Settings > On this PC > Ollama (free, local), or enter any
supported API key. RAMCheck never closes, changes or uninstalls anything without
the user clicking a button and confirming.
```

**Restricted capabilities:** Partner Center asks why each one is needed. Paste:

- **runFullTrust:** `RAMCheck is a classic Win32 desktop app (Python, Tkinter) packaged as MSIX. It needs full trust to read per-process memory usage the way Task Manager does and to show its window.`
- **unvirtualizedResources:** `Users can turn startup apps off and on exactly like Task Manager does, by writing the StartupApproved values under HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved. With registry virtualization those changes would only reach a private copy and have no effect. File system virtualization is off so settings are shared with the non-Store version in %APPDATA%\RAMCheck.`
- **allowElevation:** `Optional "Run as admin" button. Stopping third-party services and changing autostart for all users needs administrator rights. Elevation is only requested when the user clicks it, and Windows always shows the UAC prompt.`

Then **Submit for certification**. It usually takes a few days. If something is rejected, the email explains why.

## 6. Updates

Change `VERSION` in `core.py`, publish a GitHub release (see `UPDATING.md`), download the new `RAMCheck-Store.msix` from the workflow run, then in Partner Center: your app > **Update** > **Packages** > upload the new file > **Submit**. The Store version number always has to be higher than the last one.

## Listing texts

### English (United States)

**Product name:** RAMCheck

**Short description:**
See what's really using your RAM, let an AI explain every program, test your RAM for errors and clean up safely.

**Description:**
Task Manager shows how much memory a program uses. RAMCheck tells you what it is, whether you need it and what to do about it.

RAMCheck measures every running program, lets an AI of your choice give each one a clear verdict (bloatware, optional, in use, important or part of Windows) and explains it in plain words. Ask the AI follow-up questions about any program. When you're ready, Clean up closes what you picked and stops it from starting with Windows. Everything can be undone.

The Memory tab shows your RAM modules and warns when your RAM runs below its rated speed because XMP or EXPO is off. It tests free memory for errors right inside Windows and can schedule Windows' own full memory test.

Nothing happens without your click. Windows components are protected and can never be flagged. Choose a cloud AI with your own API key (Claude, OpenAI, Gemini, OpenRouter, Mistral) or run a free AI completely on your PC with Ollama or LM Studio. RAMCheck is free and open source.

**What's new in this version:**
New Memory tab: RAM module details with an XMP/EXPO check, a RAM error test, Windows Memory Diagnostic scheduling and detection of programs that keep growing.

**Product features:**
- Memory map of your whole RAM, coloured by verdict
- AI verdict and plain explanation for every running program
- Ask the AI anything about a single program
- Clean up: close bloatware and turn off its autostart in one go
- Startup tab for startup apps and services, fully reversible
- RAM error test inside Windows plus Windows Memory Diagnostic scheduling
- RAM module details with an XMP/EXPO speed check
- Spots programs whose memory keeps growing
- Cloud AI with your own key or free local AI with Ollama or LM Studio
- Cost estimate for the AI model you choose
- Open source, no account, no telemetry

**Search terms:** RAM, memory, bloatware, startup, task manager, memory test, AI

### Deutsch (Deutschland)

**Produktname:** RAMCheck

**Kurzbeschreibung:**
Sieh, was deinen Arbeitsspeicher wirklich belegt, lass dir jedes Programm von einer KI erklären, teste deinen RAM auf Fehler und räume sicher auf.

**Beschreibung:**
Der Task-Manager zeigt, wie viel Speicher ein Programm belegt. RAMCheck sagt dir, was es ist, ob du es brauchst und was du damit machen kannst.

RAMCheck misst jedes laufende Programm, lässt eine KI deiner Wahl jedes davon einordnen (Bloatware, optional, in Benutzung, wichtig oder Teil von Windows) und erklärt es verständlich. Zu jedem Programm kannst du der KI Rückfragen stellen. Mit "Clean up" schließt du anschließend, was du ausgewählt hast, und verhinderst, dass es mit Windows startet. Alles lässt sich rückgängig machen.

Der Memory-Tab zeigt deine RAM-Module und warnt, wenn dein RAM langsamer läuft als angegeben, weil XMP oder EXPO aus ist. Er testet freien Speicher direkt in Windows auf Fehler und kann den vollständigen Speichertest von Windows einplanen.

Nichts passiert ohne deinen Klick. Windows-Komponenten sind geschützt und werden nie als unnötig markiert. Wähle eine Cloud-KI mit eigenem API-Key (Claude, OpenAI, Gemini, OpenRouter, Mistral) oder lass eine kostenlose KI komplett auf deinem PC laufen, mit Ollama oder LM Studio. RAMCheck ist kostenlos und Open Source.

**Neuerungen in dieser Version:**
Neuer Memory-Tab: RAM-Module mit XMP/EXPO-Prüfung, RAM-Fehlertest, Einplanen der Windows-Speicherdiagnose und Erkennung von Programmen, deren Speicherbedarf immer weiter wächst.

**Produktfeatures:**
- Speicherkarte deines gesamten RAMs, eingefärbt nach Bewertung
- KI-Bewertung und verständliche Erklärung für jedes laufende Programm
- Stelle der KI Fragen zu einzelnen Programmen
- Clean up: Bloatware schließen und Autostart abschalten in einem Schritt
- Autostart-Tab für Programme und Dienste, komplett umkehrbar
- RAM-Fehlertest in Windows und Einplanen der Windows-Speicherdiagnose
- RAM-Module im Detail mit XMP/EXPO-Geschwindigkeitsprüfung
- Erkennt Programme, deren Speicherbedarf immer weiter wächst
- Cloud-KI mit eigenem Key oder kostenlose lokale KI mit Ollama oder LM Studio
- Kostenschätzung für das gewählte KI-Modell
- Open Source, kein Konto, keine Telemetrie

**Suchbegriffe:** RAM, Arbeitsspeicher, Bloatware, Autostart, Task-Manager, Speichertest, KI
