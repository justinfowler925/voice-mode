# The `.voicecommands` format

Apple ships an import/export format for Voice Control commands and documents none of its
internals. This is the complete per-command schema, derived empirically by reading a live
command table on macOS 26.6 and writing to it until every field's behaviour was known.

If you only take one thing from this file: **the export format and the live store are not the
same shape**, and assuming otherwise silently destroys every command you have.

---

## Two stores, two shapes

| | Shape | Where |
|---|---|---|
| **Export file** (`.voicecommands`) | Wrapped — commands live under a `CommandsTable` key | any path, you pick |
| **Live store** | **Flat** — command ids at the top level, no wrapper | `com.apple.speech.recognition.AppleSpeechRecognition.CustomCommands` |

```python
# Reading the LIVE store. There is no CommandsTable key here.
d = plistlib.loads(subprocess.check_output(
    ["defaults", "export",
     "com.apple.speech.recognition.AppleSpeechRecognition.CustomCommands", "-"]))
commands = d                      # correct
commands = d["CommandsTable"]     # KeyError
commands = d.setdefault("CommandsTable", {})   # WORST: creates an empty table,
                                               # orphans every existing command, no error
```

That third line is the trap. It writes cleanly, reports success, and your commands are gone
from the recognizer while still sitting in the file where nothing reads them.

## Export-file top level

```
CommandsTable   dict    command-id -> command dict
ExportDate      real    seconds since 2001-01-01
SystemVersion   dict    ProductBuildVersion, ProductCopyright, ProductName,
                        ProductUserVisibleVersion, ProductVersion, iOSSupportVersion
```

## Command id

```
Custom.<10 digits>.<9 digits>        e.g. Custom.808351004.970543146
```

Apple's own ids derive from a creation timestamp, but **nothing validates the number** — any
unique string matching the pattern works. Built-in commands use readable namespaced ids instead
(`System.PressItem`, `Text.SelectPhrase`, `Accessibility.DisableCommandAndControl`).

## Per-command keys

| Key | Type | Notes |
|---|---|---|
| `CustomCommands` | dict | Locale → array of spoken phrases: `{"en_US": ["punch it", "punch send"]}`. Every phrase in the array triggers the same action. |
| `CustomType` | string | See the table below. |
| `Enabled` | bool | `false` disables without deleting. **Also how you re-enable a built-in.** |
| `CustomScope` | string | `com.apple.speech.SystemWideScope` for everywhere. A bundle id scopes the command to one app. |
| `CustomModifyDate` | date | Cosmetic; nothing depends on it. |
| `CustomShortcutKeyCode` | int | Virtual key code. `Shortcut` type only. |
| `CustomShortcutModifierFlags` | int | Bitmask. `1048576` = Command (`1 << 20`). Omit for none. |
| `CustomURLStringList` | array | `["file:///Applications/Slack.app"]`. `URL` type only. Percent-encode spaces. |

## `CustomType` values

Pulled from the settings extension's own strings — these are the actions a command can take:

| Value / label | What it does |
|---|---|
| `Shortcut` | Press a keyboard shortcut |
| `URL` | Open a URL, app, file, or Finder items |
| Paste Text | Insert fixed text |
| Paste Data | Insert non-text data |
| Select Menu | **Choose a menu item by name** — underrated, see below |
| Open Shortcuts App | Run an Apple Shortcut, i.e. arbitrary logic |

## Which types actually survive

This is the part no blog post covers, and it is the difference between a command that works and
one that fires forever doing nothing. Full derivation in [mechanism-tiers.md](mechanism-tiers.md).

| Verdict | Binding |
|---|---|
| **Works** | Modified keystroke — `Cmd+Return`, `Cmd+A/C/V/Z` |
| **Works** | Accessibility action — `Select Menu`, click-by-label, native scroll |
| **Works** | `URL` / app launch |
| **Fails in Electron apps** | Bare unmodified key — Return, Escape, PageUp, PageDown |

Electron composers (Claude, Cursor, Slack, VS Code, Discord, Notion) silently drop a synthetic
bare Return. The same mechanism delivering `Cmd+Return` works. **Bind to the modified key.**

## Writing the live store

```sh
DOM=com.apple.speech.recognition.AppleSpeechRecognition.CustomCommands
defaults export "$DOM" -            # read
defaults import "$DOM" new.plist    # write
defaults delete "$DOM" <command-id> # remove ONE command
killall DictationIM                 # reload the recognizer
```

Four behaviours that cost real time:

1. **`defaults import` merges.** Modifications stick. **Deletions do not** — a key you removed
   from the imported plist stays live. Use `defaults delete` per key.
2. **Do not `killall cfprefsd` after writing.** It can flush its cache back over your write.
3. **Writing the store is not reloading the recognizer.** `killall DictationIM` after every
   change, then verify — see below.
4. **An exported file goes stale against the live table.** One command here had been changed
   from `Shortcut` to `URL` after export; the export never knew. Read the live domain.

## Verifying — the only honest instrument

`killall DictationIM` returning cleanly proves nothing. Neither does reading back the plist you
just wrote: the stored table and the running recognizer are different layers.

macOS keeps a per-command recognition counter and surfaces it in no interface:

```sh
defaults read com.apple.speech.recognition.AppleSpeechRecognition.prefs \
  DictationIMCommandCounts
```

One integer per command id, incremented on every recognition. It separates the only two
failures that matter, which are indistinguishable from the chair:

- **Counter moved, nothing happened** → recognized; the *binding* is wrong (check the tier).
- **Counter did not move** → never recognized; the *phrase* is wrong (see below).

Sibling keys in the same domain: `DictationIMLastCommandDate`, `DictationIMLastDictationDate`
(seconds since 2001-01-01), `Dictation.Streaming` (total dictations),
`DictationIMCommandAndControlEnabled`, `CACPersistentSleepState`.

## Choosing phrases

A trigger phrase competes with the sentence being transcribed. The recognizer has to decide
whether your words are a command or more dictation, and a conversational phrase loses that
decision roughly half the time.

- **Never use a phrase you would say in a sentence.** `send it`, `that's it`, `go ahead` all
  fail twice over: absorbed into the transcript when you mean them, and fired mid-sentence when
  you don't — submitting half-written messages.
- **Two or more words, no single syllables.** This is also Apple's own guidance.
- **A distinctive carrier word makes loose synonyms safe.** `punch it`, `punch send` — because
  nothing collides with "punch," you can attach as many sloppy aliases as you like.
- **You cannot talk *about* a command without firing it.** Switch to commands-only mode first
  (see [apple-internals.md](apple-internals.md)).

## Undocumented control surface

Beyond the plist there is a `notify(3)` interface, read out of the DictationIM binary. Five
recognizer modes, not the two the UI exposes:

```sh
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.NoDictation
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.NormalDictation
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.NumberDictation
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.SpellingDictation
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.SwiftCodeDictation
```

`SwiftCodeDictation` is a code-dictation mode with its own model (`SwiftCodeModel.lzfse` in the
bundle) and a `ShowCodingUserGuide` notification. Details and the full built-in command
inventory: [apple-internals.md](apple-internals.md).

## What is not available

- **No public API.** No framework, no XPC service, no entitlement. The plist plus the Settings
  UI plus `.voicecommands` import is the entire surface.
- **The built-in command phrases are compiled into the binary.** The catalog at
  `/System/Library/Input Methods/DictationIM.app/Contents/Resources/BuiltinCommandsCatalog.plist`
  lists 161 command *identifiers*; the spoken wording is not shipped as readable strings. Say
  `show commands` to see the real phrasing for the app you are in.
- **Vocabulary import format unknown.** The Vocabulary pane has Import/Export, but the file
  schema is not discoverable from the settings extension. `Text.AddSelectionToVocabulary` adds
  words by voice, which routes around it.

---

*Derived on macOS 26.6, 2026-08-14. Every claim here was either read out of an Apple binary or
observed changing behaviour on a live system. Where something is inferred rather than verified,
it says so.*
