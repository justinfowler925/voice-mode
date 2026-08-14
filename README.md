# voice-mode

**Hands-free voice control on macOS, without the evening I spent finding out how.**

No hotkey. No third-party dictation app. No background daemons. One phrase to send, in every
app, and a tool that tells you why a command isn't working instead of leaving you guessing.

**Setup guide, full command reference and troubleshooting:
[justinfowler.com/voice-mode](https://justinfowler.com/voice-mode.html)** — start there if you just
want it working. This README is the developer view.

```sh
git clone https://github.com/justinfowler925/voice-mode && cd voice-mode
./bin/voice-mode doctor
```

---

## Why this exists

macOS Voice Control is genuinely good and almost completely undocumented past the settings
pane. Apple ships an import/export format and documents none of its internals. There is no
public API. There is no community repo of shared command sets. The search results are content
farms, and several of them are wrong — a widely-copied claim that macOS has no custom
vocabulary is false, the Vocabulary pane has been there for years.

So everyone who tries this rediscovers the same handful of traps alone. The expensive one:

> **A synthetic bare `Return` is silently dropped by every Electron app** — Claude, Cursor,
> Slack, VS Code, Discord, Notion. `Cmd+Return` from the identical mechanism works fine.

If you don't know that, you conclude keystrokes are unusable, and you go build an
accessibility-tree walker that breaks every time the app's layout shifts. I did. It took hours,
across two wrong theories, and the whole thing was one test wide.

## The working setup

Apple Voice Control listening continuously, plus one command bound to `Cmd+Return`.

```
punch it        ->  Cmd+Return      send, in any app
go to cursor    ->  opens Cursor    switch apps
hands / talk    ->  mode switch     stop / resume transcribing
click <name>    ->  built-in        press anything with a visible label
show numbers    ->  built-in        badge everything clickable when it hasn't
show commands   ->  built-in        Apple's real phrasing, for the app you're in
```

That's it. It replaced four launchd daemons and eleven helper apps.

## What's here

| | |
|---|---|
| [`docs/voicecommands-format.md`](docs/voicecommands-format.md) | **The complete `.voicecommands` schema.** Every per-command key, derived by reading a live table and writing to it until each field's behaviour was known. Not documented anywhere else. |
| [`docs/mechanism-tiers.md`](docs/mechanism-tiers.md) | Why a command fires and does nothing, and how to predict it from the binding alone. |
| [`docs/apple-internals.md`](docs/apple-internals.md) | The undocumented `notify(3)` surface — five recognizer modes including a code-dictation mode — and the 161-command built-in catalog. |
| [`bin/voice-mode`](bin/voice-mode) | `doctor`, `list`, `build`. Python 3 stdlib only. |
| [`sets/`](sets/) | Readable JSON command sets → importable `.voicecommands` files. |
| [`reference/card.html`](reference/card.html) | An on-screen cheat card you can park in a corner. |

## `voice-mode doctor`

The tool this project exists for. macOS keeps a per-command recognition counter and surfaces it
in no interface anywhere. Without it you cannot tell these apart:

- **it never heard me** → the phrase is wrong
- **it heard me and the action did nothing** → the binding is wrong

They are indistinguishable from the chair and have nothing in common as bugs. `doctor` reads
the counter, sorts every command into a mechanism tier, and names the ones that cannot work:

```
  [works ] modified-key — survives Electron composers
      punch it / punch send                        Cmd+Return     fired 23

  [FAILS ] bare-key — SWALLOWED by Claude / Cursor / Slack / VS Code
      press return / hit return / enter it         Return         fired 2

FINDINGS
  ! 2 command(s) bound to a BARE KEY — silently dropped by Electron composers.
```

It also separates *untested* from *broken*, because a command that has never fired is not
evidence of anything, and flags built-ins that a custom command has silently switched off.

## Choosing phrases

The single highest-leverage decision, and the one everyone gets wrong first.

A trigger phrase competes with the sentence being transcribed. The recognizer must decide
whether your words are a command or more dictation, and **a conversational phrase loses that
decision about half the time.**

Worse, it fires when you didn't mean it. `that's it` and `go ahead` occur constantly in normal
speech — each one submits a half-written message.

- Use something you would never say in a sentence.
- Two or more words, no single syllables. (Also Apple's own guidance.)
- A distinctive carrier word makes loose aliases safe: nothing collides with "punch," so
  `punch it` and `punch send` can both exist with no risk.
- You cannot talk *about* a command without firing it — switch to commands-only mode first.

## Testing

```sh
./tests/run
```

31 checks. They exist to prove the gates **reject**, not to cover lines — every guard is fed a
known violation and asserted to refuse it. Plus: shipped `.voicecommands` files must match a
fresh rebuild from their `.json`, and an empty set fails rather than passing as "clean."

**There is no CI here, deliberately.** GitHub Actions cannot start a run in this repository —
a workflow whose only step is `echo hello` completes as *failure* in about four seconds with
**zero steps executed** and no annotation. That is an account-level condition, not a code
problem, and a permanently red check would misrepresent working code. `./tests/run` is the gate.
If you fork this, add your own workflow calling that script; it needs nothing but python3.

## Status

Early. Verified on macOS 26.6 against Claude, Cursor and Slack. Everything documented here was
either read out of an Apple binary or observed changing behaviour on a live system; where a
claim is inferred rather than verified, it says so.

Contributions especially wanted for: the Vocabulary import file format (undiscovered), which
apps drop which synthetic keys, and `Select Menu` command sets for specific apps.

## Reading

- **[justinfowler.com/voice-mode](https://justinfowler.com/voice-mode.html)** — setup in five
  minutes, the command reference, and troubleshooting by symptom. For novices and developers both.
- **[The Voice Optimization Stack](https://justinfowler.com/writing/voice-optimization-stack.html)**
  — the seven layers between your mouth and a computer doing what you meant, ranked by leverage,
  with the measurement for each.
- **[Heard, Not Obeyed](https://justinfowler.com/writing/heard-not-obeyed.html)** — the evening
  this came out of. Seven dead ends and three wrong conclusions, written down so nobody repeats them.

## License

MIT.
