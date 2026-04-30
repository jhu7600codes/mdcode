# MDCode

A scripting language that uses markdown heading syntax for commands.

```
#import lib-mdcode
#import lib-autoVar

#var name (create) | MDCode
#print | Hello from + name | !

#os | uname -r > kernel
###print | kernel: + kernel

#exit | 0
```

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/jhu7600codes/mdcode/main/install.sh | bash
```

Requires Python 3.10+, no pip installs needed.

## Usage

```bash
mdcode run yourfile.md
```

## Syntax

| syntax | meaning |
|---|---|
| `#cmd` | top level command |
| `###cmd` | child command (+2 depth) |
| `##cmd` | child accessing parent onetimeVar (+1) |
| `\| value` | string / number / bool literal |
| `varName` | variable reference |
| `+` | concatenation |
| `>` | assignment |
| `/` | pipe |

## Libraries

- `lib-mdcode` — core stdlib, always import
- `lib-autoVar` — auto-exposes `strVar` and log vars
- `lib-visual` — native GTK window with navbar and webview

## Examples

See [`/examples`](./examples) for `test_full.md`, `mdcodeterm.md`, and `visualtest.md`.

## Website

[jhu7600codes.github.io/mdcode](https://jhu7600codes.github.io/mdcode)

---

made by [jhu7600codes](https://github.com/jhu7600codes)
