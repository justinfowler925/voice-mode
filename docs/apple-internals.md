# Apple internals

Everything here was read out of an Apple binary or bundle on macOS 26.6, not inferred.

## The undocumented `notify(3)` surface

Read from the `DictationIM` binary. **Five recognizer modes — the UI exposes two.**

```sh
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.NoDictation
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.NormalDictation
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.NumberDictation
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.SpellingDictation
notifyutil -p com.apple.VoiceControl.SetRecognizerMode.SwiftCodeDictation
```

Also present: `RecognizerModeChanged`, `LoggingPrivacyChanged`, `ShowCodingUserGuide`,
`requestingSiriOpen`, `requestingSiriClose`.

`SwiftCodeDictation` is a **code-dictation mode** with its own language model
(`SwiftCodeModel.lzfse` in the bundle) and a matching user guide notification. Undocumented,
unexposed in Settings, and reachable in one line. `SpellingDictation` is letter-by-letter;
`NumberDictation` is numeric.

Wrap any of these in a `URL`-type command pointing at a two-line shell app and you have a
spoken mode switch. That is how `hands` / `talk` work in this repo.

## Trap: never put a script inside ~/Library/Application Support

A `URL`-type command pointing at a small app bundle is the standard way to reach the notify
surface above. **Do not keep that app, or any script it runs, under
`~/Library/Application Support/`.**

That directory is TCC-protected App Data. Running an interpreter against a script that lives
there turns an ordinary file read into a *"Python wants to access data from other applications"*
prompt — on **every** launch, not once.

And it cannot be granted away permanently. Tools like `uv` install interpreters at
version-pinned paths (`cpython-3.13.13-...`) with the stable name as a symlink; TCC records the
**resolved** path, so every patch upgrade is a brand-new binary identity and prompts again. The
grant you clicked last month is still there, attached to a path nothing runs anymore.

Keep wrapper apps and their scripts somewhere ordinary — `~/.voice-mode/`, `~/.config/`, a repo
checkout. The command's `CustomURLStringList` can point anywhere.

## Where the phrases live, and don't

- **Command catalog:** `/System/Library/Input Methods/DictationIM.app/Contents/Resources/BuiltinCommandsCatalog.plist`
  — `HistoricalCommandFrequencies` holds every built-in command **identifier**;
  `KeyboardKeyProperties` holds the 82 key names usable in `press <key>`;
  `OrderedCommandSetGroupIdentifiers` is `Dictation`, `Extended`, `Custom`.
- **The spoken phrasing is compiled into the binary.** `en.lproj/BuiltinCommands.strings` holds
  only 34 placeholder tokens (`'phrase'`, `'application name'`, `'number'`), not commands.
  `BuiltinCommandStrings/` ships `zh_HK.strings` and nothing else.
- **To see real phrasing, say `show commands`** — it renders the live list for the frontmost app.

## No public API

No framework, no XPC service, no entitlement, no documented plist. The entire supported surface
is the Settings pane plus `.voicecommands` import/export. `DictationIM`'s bundle id is
`com.apple.inputmethod.ironwood`; it declares no service interface.

Private frameworks in the neighbourhood (none with a usable command API): `CoreSpeech`,
`CoreSpeechFoundation`, `CoreEmbeddedSpeechRecognition`, `LocalSpeechRecognitionBridge`,
`AdaptiveVoiceShortcuts`, `LiveSpeechServices`.

## Vocabulary

The Vocabulary pane exists (`AX.VoiceControl.axVoiceControlVocabulary`) and has Import/Export —
the settings extension carries the whole `VocabularyImportExport.*` string family, including
"This will permanently delete them from all your devices," so entries **sync across devices**.

**The import file format is not discoverable** from the settings extension. Unresolved. But
`Text.AddSelectionToVocabulary` adds words by voice, which routes around it entirely: select the
word, say the command.

## The 161 built-in commands

Identifiers, not phrases. Most read like their phrase; say `show commands` for the real
wording. Notable ones are called out after the list.

### System (104)

```
Copy
Create Command
Cut
Decrease Volume
Double Tap
Double Tap Item
Go Back
Go Home
Hide Element Names
Hide Grid
Hide Labels
Increase Volume
Key Down Arrow
Key Left Arrow
Key Right Arrow
Key Up Arrow
Lock Screen
Long Press
Long Press Item
Mute
Overlay Choose All Labels
Overlay Choose Label
Overlay Double Tap Label
Overlay Long Press Label
Overlay Pan Down At Label
Overlay Pan Left At Label
Overlay Pan Right At Label
Overlay Pan Up At Label
Overlay Press Label
Overlay Show Actions For Label
Overlay Swipe Down At Label
Overlay Swipe Left At Label
Overlay Swipe Right At Label
Overlay Swipe Up At Label
Overlay Zoom In At Label
Overlay Zoom Out At Label
Pan Down
Pan Down At Item
Pan Left
Pan Left At Item
Pan Right
Pan Right At Item
Pan Up
Pan Up At Item
Paste
Press Item
Redo
Repeat Previous Command
Rotate Device Landscape
Rotate Device Portrait
S O S
Scroll Page Down
Scroll Page Left
Scroll Page Right
Scroll Page Up
Scroll To Bottom
Scroll To Left Edge
Scroll To Right Edge
Scroll To Top
Show Actions For Item
Show Application Switcher
Show Commands
Show Control Center
Show Dock
Show Element Names
Show Element Names Continuously
Show Element Numbers Continuously
Show Grid
Show Grid Numbers Continuously
Show Grid Numbers Continuously With Number Of Columns
Show Grid Numbers Continuously With Number Of Columns And Rows
Show Grid Numbers Continuously With Number Of Rows
Show Grid With Number Of Columns
Show Grid With Number Of Columns And Rows
Show Grid With Number Of Rows
Show Labels
Show Notification Center
Show Training
Show Vocabulary
Sleep Listening
Speak Screen
Start Command Mode
Start Dictation Mode
Start Recording Commands
Start Siri
Start Spotlight
Start Spotlight Search
Start Web Search
Swipe Down
Swipe Down At Item
Swipe Left
Swipe Left At Item
Swipe Right
Swipe Right At Item
Swipe Up
Swipe Up At Item
Switch To Application
Tap
Undo
Unmute
Zoom In
Zoom In At Item
Zoom Out
Zoom Out At Item
```

### Text (55)

```
Add Selection To Vocabulary
Capitalize Phrase
Capitalize Selection
Change Phrase
Correct Phrase
Correct Selection
Delete Selection
Editing Completion
Format Bold
Format Bold Phrase
Format Italic
Format Italic Phrase
Format Underline
Format Underline Phrase
Go To End Of Document
Go To End Of Line
Go To End Of Paragraph
Go To End Of Selection
Go To End Of Sentence
Go To End Of Word
Go To Start Of Document
Go To Start Of Line
Go To Start Of Paragraph
Go To Start Of Selection
Go To Start Of Sentence
Go To Start Of Word
Insert Date
Insert Named Emoji
Lowercase Phrase
Lowercase Selection
Select Current Character
Select Current Line
Select Current Paragraph
Select Current Sentence
Select Current Word
Select Emoji With Phrase
Select Entire Document
Select Next
Select Next Character
Select Next Line
Select Next Paragraph
Select Next Sentence
Select Next Word
Select Phrase
Select Phrase Through Phrase
Select Previous
Select Previous Character
Select Previous Line
Select Previous Paragraph
Select Previous Sentence
Select Previous Word
Select Prior Insertion
Unselect
Uppercase Phrase
Uppercase Selection
```

### Accessibility (1)

```
Disable Command And Control
```

### Dictation (1)

```
Literal
```

### Nameable keyboard keys (82)

Usable in `press <key>`.

```
KeyboardKeyName.0, KeyboardKeyName.1, KeyboardKeyName.2, KeyboardKeyName.3, KeyboardKeyName.4, KeyboardKeyName.5, KeyboardKeyName.6, KeyboardKeyName.7, KeyboardKeyName.8, KeyboardKeyName.9, KeyboardKeyName.A, KeyboardKeyName.ArrowDown, KeyboardKeyName.ArrowLeft, KeyboardKeyName.ArrowRight, KeyboardKeyName.ArrowUp, KeyboardKeyName.B, KeyboardKeyName.C, KeyboardKeyName.D, KeyboardKeyName.Delete, KeyboardKeyName.E, KeyboardKeyName.End, KeyboardKeyName.Equals, KeyboardKeyName.Escape, KeyboardKeyName.F, KeyboardKeyName.F1, KeyboardKeyName.F10, KeyboardKeyName.F11, KeyboardKeyName.F12, KeyboardKeyName.F2, KeyboardKeyName.F3, KeyboardKeyName.F4, KeyboardKeyName.F5, KeyboardKeyName.F6, KeyboardKeyName.F7, KeyboardKeyName.F8, KeyboardKeyName.F9, KeyboardKeyName.ForwardDelete, KeyboardKeyName.G, KeyboardKeyName.H, KeyboardKeyName.Home, KeyboardKeyName.Hyphen, KeyboardKeyName.I, KeyboardKeyName.J, KeyboardKeyName.K, KeyboardKeyName.Keypad0, KeyboardKeyName.Keypad1, KeyboardKeyName.Keypad2, KeyboardKeyName.Keypad3, KeyboardKeyName.Keypad4, KeyboardKeyName.Keypad5, KeyboardKeyName.Keypad6, KeyboardKeyName.Keypad7, KeyboardKeyName.Keypad8, KeyboardKeyName.Keypad9, KeyboardKeyName.KeypadAdd, KeyboardKeyName.KeypadClear, KeyboardKeyName.KeypadDecimal, KeyboardKeyName.KeypadDivide, KeyboardKeyName.KeypadEnter, KeyboardKeyName.KeypadEquals, KeyboardKeyName.KeypadMultiply, KeyboardKeyName.KeypadSubtract, KeyboardKeyName.L, KeyboardKeyName.M, KeyboardKeyName.N, KeyboardKeyName.O, KeyboardKeyName.P, KeyboardKeyName.PageDown, KeyboardKeyName.PageUp, KeyboardKeyName.Q, KeyboardKeyName.R, KeyboardKeyName.Return, KeyboardKeyName.S, KeyboardKeyName.Space, KeyboardKeyName.T, KeyboardKeyName.Tab, KeyboardKeyName.U, KeyboardKeyName.V, KeyboardKeyName.W, KeyboardKeyName.X, KeyboardKeyName.Y, KeyboardKeyName.Z
```

## Worth knowing about

- **`Text.AddSelectionToVocabulary`** — add a word to the vocabulary by voice. Routes around the
  undiscovered import format.
- **`System.CreateCommand`** / **`System.StartRecordingCommands`** — create new commands by
  voice, no plist editing.
- **`Text.SelectPhrase`**, **`Text.SelectPhraseThroughPhrase`**, **`Text.CorrectPhrase`**,
  **`Text.ChangePhrase`** — select and fix arbitrary spoken text by quoting it. Far better than
  character-level editing.
- **`System.ShowGrid`** and its row/column variants — a numbered grid over the whole screen. The
  general answer to any control with no accessible name.
- **`System.RepeatPreviousCommand`**, **`System.ShowVocabulary`**, **`System.ShowTraining`**,
  **`System.SpeakScreen`**, **`System.ShowCommands`**.
- **`Dictation.Literal`** — dictate a phrase without command interpretation. The escape hatch
  for saying a trigger word without firing it.
