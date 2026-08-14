#!/usr/bin/env python3
"""Tests for voice-mode.

The point of these is not coverage — it is proving the gates BITE. A gate nobody has
watched fail is decoration, so every guard here is fed a known violation and asserted to
reject it, not merely asserted to exist on a clean input.

Run: python3 tests/test_voice_mode.py
"""

import importlib.machinery
import importlib.util
import json
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "voice-mode"

spec = importlib.util.spec_from_loader("vm", importlib.machinery.SourceFileLoader("vm", str(BIN)))
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}{'  — ' + detail if detail and not cond else ''}")


def build(spec_obj):
    """Run the real CLI build path and return (plist, stdout)."""
    with tempfile.TemporaryDirectory() as d:
        sp = Path(d) / "s.json"
        out = Path(d) / "o.voicecommands"
        sp.write_text(json.dumps(spec_obj))
        r = subprocess.run([sys.executable, str(BIN), "build", str(sp), "-o", str(out)],
                           capture_output=True, text=True)
        data = plistlib.loads(out.read_bytes()) if out.exists() else {}
        return data, r.stdout + r.stderr


print("classify() — tier assignment")

check("Cmd+Return is the surviving tier",
      vm.classify({"CustomType": "Shortcut", "CustomShortcutKeyCode": 36,
                   "CustomShortcutModifierFlags": vm.CMD_FLAG})[0] == vm.TIER_OK_MOD)

check("bare Return is the FAILING tier",
      vm.classify({"CustomType": "Shortcut", "CustomShortcutKeyCode": 36})[0] == vm.TIER_BAD_BARE)

check("bare Escape is the FAILING tier",
      vm.classify({"CustomType": "Shortcut", "CustomShortcutKeyCode": 53,
                   "CustomShortcutModifierFlags": 0})[0] == vm.TIER_BAD_BARE)

check("Shift+Return counts as modified",
      vm.classify({"CustomType": "Shortcut", "CustomShortcutKeyCode": 36,
                   "CustomShortcutModifierFlags": vm.SHIFT_FLAG})[0] == vm.TIER_OK_MOD)

check("app launch is a surviving tier",
      vm.classify({"CustomType": "URL",
                   "CustomURLStringList": ["file:///Applications/Slack.app"]})[0] == vm.TIER_OK_LAUNCH)

check("menu selection is a surviving tier",
      vm.classify({"CustomType": "SelectMenu", "CustomMenuPath": "File>New"})[0] == vm.TIER_OK_AX)

check("binding string names the modifier",
      vm.classify({"CustomType": "Shortcut", "CustomShortcutKeyCode": 36,
                   "CustomShortcutModifierFlags": vm.CMD_FLAG})[1] == "Cmd+Return")


print("\nbuild() — the gates must REJECT, not warn")

d, out = build({"commands": [{"say": ["nope"], "key": "return"}]})
check("bare key is REFUSED by default", len(d.get("CommandsTable", {})) == 0,
      f"emitted {len(d.get('CommandsTable', {}))} commands")
check("...and says why", "bare key" in out.lower())

d, _ = build({"commands": [{"say": ["yep"], "key": "return", "mods": ["cmd"]}]})
check("modified key is ACCEPTED", len(d.get("CommandsTable", {})) == 1)

d, _ = build({"commands": [{"say": ["forced"], "key": "return", "allow_bare": True}]})
check("allow_bare forces it through (escape hatch works)",
      len(d.get("CommandsTable", {})) == 1)

d, out = build({"commands": [{"say": ["bad"], "key": "nosuchkey", "mods": ["cmd"]}]})
check("unknown key name is REFUSED", len(d.get("CommandsTable", {})) == 0)
check("...and names the bad key", "nosuchkey" in out)

d, out = build({"commands": [{"say": ["bad"], "key": "a", "mods": ["hyper"]}]})
check("unknown modifier is REFUSED", len(d.get("CommandsTable", {})) == 0)

d, _ = build({"commands": [{"say": [], "key": "a", "mods": ["cmd"]}]})
check("a command with no phrases is REFUSED", len(d.get("CommandsTable", {})) == 0)

d, _ = build({"commands": [{"say": ["orphan"]}]})
check("a command with no action is REFUSED", len(d.get("CommandsTable", {})) == 0)


print("\nexport format — the shape that orphans commands if you get it wrong")

d, _ = build({"commands": [{"say": ["x"], "key": "a", "mods": ["cmd"]}]})
check("export IS wrapped in CommandsTable", "CommandsTable" in d)
check("export carries ExportDate + SystemVersion",
      "ExportDate" in d and "SystemVersion" in d)
c = list(d["CommandsTable"].values())[0]
check("phrases land under the en_US locale key",
      c.get("CustomCommands", {}).get("en_US") == ["x"])
check("Cmd flag is written as 1048576", c.get("CustomShortcutModifierFlags") == 1048576)
check("commands are enabled on import", c.get("Enabled") is True)
check("scope defaults to system-wide",
      c.get("CustomScope") == "com.apple.speech.SystemWideScope")


print("\nshipped sets must contain no failing bindings")

for f in sorted((ROOT / "sets").glob("*.json")):
    obj = json.loads(f.read_text())
    d, _ = build(obj)
    table = d.get("CommandsTable", {})
    bad = [cid for cid, c in table.items() if vm.classify(c)[0] == vm.TIER_BAD_BARE]
    declared = len(obj.get("commands", []))
    check(f"{f.name}: every emitted binding survives", not bad, f"{bad}")
    # A set that silently emits nothing would pass the check above. Assert the denominator.
    check(f"{f.name}: emitted a non-zero share of {declared} declared", len(table) > 0,
          "emitted 0 — the set is broken, not clean")



print("\nzero-state — a verdict on an empty set is not a pass")

import io, contextlib
_real_read = vm._read
vm._read = lambda d: {}
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    class _A: pass
    rc_empty = vm.cmd_doctor(_A())
vm._read = _real_read
txt = buf.getvalue()
check("empty config does NOT report 'no binding problems'",
      "No binding problems found" not in txt)
check("empty config says nothing to check", "NOTHING TO CHECK" in txt)
check("empty config exits non-zero (2)", rc_empty == 2, f"got {rc_empty}")

print("\n" + "=" * 56)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    for f in FAIL:
        print(f"  FAILED: {f}")
sys.exit(1 if FAIL else 0)
