# Mechanism tiers

**A voice command's reliability is a property of what it's bound to, not the app it lands in.**

Sort your commands into these four tiers and you can predict which ones work before testing any
of them. This is the single most useful thing in this repo; everything else is detail.

| Tier | Binding | Verdict |
|---|---|---|
| `modified-key` | `Cmd+Return`, `Cmd+A/C/V/Z/N` | **Works** |
| `accessibility` | click-by-label, `Select Menu`, native scroll | **Works** — needs the control to have a name |
| `app-launch` | open an app, file, or URL | **Works** — nothing in the path to swallow it |
| `bare-key` | `Return`, `Escape`, `PageUp`, `PageDown` | **Fails** in Electron composers |

## The finding

Electron apps — Claude, Cursor, Slack, VS Code, Discord, Notion — render their composers as
HTML rather than native controls. A synthetic **bare** `Return` is delivered to them and quietly
dropped. No error, no bounce, nothing in any log.

`Cmd+Return`, posted by the *identical* mechanism, works in all of them.

Measured: a send command bound to bare Return fired **8 times across two rounds and sent zero
messages**. Rebound to `Cmd+Return`, it fired 7 times and landed in Claude, Cursor and Slack.

The boundary is not native-versus-web, and not real-versus-synthetic. **It is which key.**

## Why this costs so much time

The failure is invisible in exactly the wrong way. The command *is* recognized — the OS counter
increments — so every check you can think of looks healthy:

- the phrase was heard ✓
- the command fired ✓
- the config is correct ✓
- no error anywhere ✓
- nothing happened ✗

Faced with that, the natural conclusion is "synthetic keystrokes don't work in these apps," and
the natural next move is to go around the keyboard entirely: walk the accessibility tree, find
the send button, press it. That's a real amount of work and it's brittle — an Electron tree
shifts with layout, so it works often enough to ship and then fails constantly.

**One test — the same command with a modifier — makes all of that unnecessary.** Never
generalise from one key to the whole input path.

## Accessibility actions, and their limit

`click <button name>` presses a control by the name the app publishes. It's excellent, and it's
app-agnostic by construction: you say one phrase, macOS reads the label in whatever is frontmost.

**It is not universal.** It needs the control to *have* an accessible name. Cursor's send arrow
is an icon button with none, so the command fired 13 times and pressed nothing.

So: accessibility actions remove the need for per-app **code**. They don't remove the need for a
per-app **name**. When there isn't one, `show numbers` indexes everything clickable whether it's
labelled or not, and `Select Menu` works whenever the action exists in a menu — menu items are
always named.

## The shadowing trap

**A custom command silently disables the built-in that shares its phrase.**

`scroll up` / `scroll down` hand-bound to bare `PageUp`/`PageDown` left
`System.ScrollPageUpAndCount` and `...DownAndCount` — Voice Control's own accessibility-based
scrolling — sitting at `Enabled = false`. A working native action had been replaced by a broken
keystroke, invisibly, and nothing anywhere said so.

**Check whether the platform already ships a verb before binding it yourself.** The native
command almost certainly rides a better tier. Fix is to delete the custom command and set
`Enabled = true` on the system one; `voice-mode doctor` flags disabled built-ins for this reason.

## Diagnosing in five seconds

```sh
./bin/voice-mode doctor
```

When a command does nothing, **check its tier before debugging the app.** If it's `bare-key`,
you already have your answer. If it isn't, read the counter:

- **counter moved, nothing happened** → recognized; the binding is wrong
- **counter never moved** → not recognized; the phrase is wrong

Those two have nothing in common as bugs, and guessing between them is where the hours go.
