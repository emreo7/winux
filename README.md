# linuxConverter

![Python](https://img.shields.io/badge/python-3.10%2B-blue)

A terminal application that translates Linux CLI commands into their Windows equivalents — either **CMD** or **PowerShell** — and executes them directly. Designed for developers who think in Linux but work on Windows.

---

## Features

- Translate and execute a wide range of Linux commands with flag support
- Supports **piped pipelines** (`ls | grep foo | head -5`)
- Choose between **CMD** or **PowerShell** as the translation target
- Interactive REPL with a familiar shell-like prompt
- Tab completion for directory paths
- Warnings and PowerShell suggestions for unsupported CMD commands
- Tracks your current working directory (`cd` updates the session)

---

## Supported Commands

### Filesystem

| Linux | PowerShell | CMD |
|-------|-----------|-----|
| `pwd` | `Get-Location` | `cd` |
| `ls` | `Get-ChildItem` | `dir` |
| `ls -a` | `Get-ChildItem -Force` | `dir /a` |
| `ls -R` | `Get-ChildItem -Recurse` | `dir /s` |
| `cd <path>` | `Set-Location <path>` | `cd <path>` |
| `mkdir <path>` | `New-Item -ItemType Directory -Path <path> -Force` | `mkdir <path>` |
| `mkdir -p <path>` | `New-Item -ItemType Directory -Path <path> -Force` | `mkdir <path>` |
| `touch <file>` | `New-Item -ItemType File -Path <file> -Force` | `type NUL > "<file>"` |
| `rm <file>` | `Remove-Item -Force <file>` | `del /f <file>` |
| `rm -r <dir>` | `Remove-Item -Recurse -Force <dir>` | `rmdir /s /q <dir>` |
| `rm -rf <dir>` | `Remove-Item -Recurse -Force <dir>` | `rmdir /s /q <dir>` |
| `cp <src> <dst>` | `Copy-Item <src> <dst>` | `copy <src> <dst>` |
| `cp -r <src> <dst>` | `Copy-Item -Recurse <src> <dst>` | `xcopy <src> <dst> /e /i /h` |
| `mv <src> <dst>` | `Move-Item <src> <dst>` | `move <src> <dst>` |
| `ln -s <target> <link>` | `New-Item -ItemType SymbolicLink -Path <link> -Target <target>` | *(PowerShell recommended)* |
| `ln <target> <link>` | `New-Item -ItemType HardLink -Path <link> -Target <target>` | *(PowerShell recommended)* |
| `find <path> -name <pat>` | `Get-ChildItem -Path <path> -Recurse -Filter <pat>` | *(PowerShell recommended)* |
| `find <path> -type d` | `Get-ChildItem -Recurse \| Where-Object { $_.PSIsContainer }` | *(PowerShell recommended)* |
| `du -sh <path>` | `(Get-ChildItem <path> -Recurse \| Measure-Object -Property Length -Sum).Sum` | *(PowerShell recommended)* |
| `df` | `Get-PSDrive -PSProvider FileSystem` | *(PowerShell recommended)* |
| `chmod` | *(no direct equivalent — use `Set-Acl`)* | *(not supported)* |
| `chown` | *(no direct equivalent — use `Set-Acl`)* | *(not supported)* |

### Text & Content

| Linux | PowerShell | CMD |
|-------|-----------|-----|
| `cat <file>` | `Get-Content <file>` | `type <file>` |
| `cat -n <file>` | `Get-Content <file> \| Select-String '.' \| ForEach-Object { $_.LineNumber ... }` | *(PowerShell recommended)* |
| `echo <text>` | `echo <text>` | `echo <text>` |
| `grep <pat> <file>` | `Select-String "<pat>" <file>` | `findstr "<pat>" <file>` |
| `grep -i <pat>` | `Select-String "<pat>"` *(case-insensitive by default)* | `findstr /i "<pat>"` |
| `grep -v <pat>` | `Select-String -NotMatch "<pat>"` | *(not directly supported)* |
| `grep -r <pat> <dir>` | `Select-String "<pat>" -Path <dir> -Recurse` | `findstr /s "<pat>"` *(with warning)* |
| `grep -n <pat>` | `Select-String "<pat>" \| ForEach-Object { $_.LineNumber + ':' + $_.Line }` | *(PowerShell recommended)* |
| `grep -l <pat>` | `Select-String "<pat>" \| Select-Object -ExpandProperty Path` | *(PowerShell recommended)* |
| `grep -c <pat>` | `Select-String "<pat>" \| Measure-Object \| Select-Object -ExpandProperty Count` | *(PowerShell recommended)* |
| `head -n <n>` | `Select-Object -First <n>` *(pipeline)* | *(not supported)* |
| `tail -n <n>` | `Select-Object -Last <n>` *(pipeline)* | *(not supported)* |
| `sort` | `Sort-Object` | `sort` |
| `sort -r` | `Sort-Object -Descending` | `sort /r` |
| `sort -u` | `Sort-Object -Unique` | *(PowerShell recommended)* |
| `uniq` | `Select-Object -Unique` | *(PowerShell recommended)* |
| `wc -l <file>` | `(Get-Content "<file>").Count` | *(PowerShell recommended)* |
| `wc -w <file>` | `((Get-Content "<file>") -join " ").Split() \| Measure-Object ...` | *(PowerShell recommended)* |
| `wc -c <file>` | `(Get-Content -Raw "<file>").Length` | *(PowerShell recommended)* |
| `diff <f1> <f2>` | `Compare-Object (Get-Content "<f1>") (Get-Content "<f2>")` | *(PowerShell recommended)* |
| `sed 's/old/new/' <file>` | `(Get-Content "<file>") -replace "old","new" \| Set-Content "<file>"` | *(PowerShell recommended)* |
| `awk` | *(no direct equivalent)* | *(not supported)* |

### System

| Linux | PowerShell | CMD |
|-------|-----------|-----|
| `ps` | `Get-Process` | *(PowerShell recommended)* |
| `ps aux` | `Get-Process` | *(PowerShell recommended)* |
| `kill <pid>` | `Stop-Process -Id <pid>` | *(PowerShell recommended)* |
| `kill -9 <pid>` | `Stop-Process -Id <pid> -Force` | *(PowerShell recommended)* |
| `sleep <n>` | `Start-Sleep <n>` | `timeout /t <n> /nobreak` |
| `whoami` | `whoami` | `whoami` |
| `date` | `Get-Date` | `date /t` |
| `clear` | `Clear-Host` | `cls` |
| `history` | `Get-History` | `doskey /history` |
| `env` | `Get-ChildItem Env:` | *(PowerShell recommended)* |
| `export KEY=val` | `$env:KEY = "val"` | *(PowerShell recommended)* |
| `which <cmd>` | `(Get-Command "<cmd>").Source` | *(PowerShell recommended)* |
| `man <cmd>` | `Get-Help <cmd> -Full` | *(PowerShell recommended)* |
| `uname -a` | `[System.Environment]::OSVersion \| Select-Object -ExpandProperty VersionString` | *(PowerShell recommended)* |
| `uptime` | `(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime` | *(PowerShell recommended)* |
| `free` | `Get-CimInstance Win32_OperatingSystem \| Select-Object TotalVisibleMemorySize,FreePhysicalMemory` | *(PowerShell recommended)* |

### Archive

| Linux | PowerShell | CMD |
|-------|-----------|-----|
| `tar -czf <archive> <src>` | `Compress-Archive -Path <src> -DestinationPath <archive>` | *(PowerShell recommended)* |
| `tar -xzf <archive>` | `Expand-Archive -Path <archive> -DestinationPath .` | *(PowerShell recommended)* |
| `zip <archive> <src>` | `Compress-Archive -Path <src> -DestinationPath <archive>` | *(PowerShell recommended)* |
| `unzip <archive>` | `Expand-Archive -Path <archive> -DestinationPath .` | *(PowerShell recommended)* |

### Network

| Linux | PowerShell | CMD |
|-------|-----------|-----|
| `ping <host>` | `ping <host>` | `ping <host>` |
| `curl <url>` | `Invoke-WebRequest -Uri "<url>" \| Select-Object -ExpandProperty Content` | *(PowerShell recommended)* |
| `curl -o <file> <url>` | `Invoke-WebRequest -Uri "<url>" -OutFile "<file>"` | *(PowerShell recommended)* |
| `wget <url>` | `Invoke-WebRequest -Uri "<url>" -OutFile <filename>` | *(PowerShell recommended)* |
| `ifconfig` | `Get-NetIPAddress` | `ipconfig` |
| `ip addr` | `Get-NetIPAddress` | `ipconfig` |
| `ip link` | `Get-NetAdapter` | `ipconfig` |
| `ip route` | `Get-NetRoute` | `ipconfig` |
| `netstat` | `Get-NetTCPConnection` | `netstat` |
| `ssh` | passed through as-is | passed through as-is |
| `scp` | passed through as-is | passed through as-is |

### Dev Tools (passed through)

`git`, `npm`, `pip`, `python`, `python3`, `node` — all arguments passed through unchanged to both PowerShell and CMD.

---

## Installation

**Requirements:** Python 3.10+

```bash
git clone https://github.com/emreo7/winux.git
cd winux
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

> **Note:** The repository folder is named `winux`, but the package name is `linuxConverter`. You run it with `python -m linuxConverter`.

---

## Usage

```bash
python -m linuxConverter [--cmd | --powershell | --target <shell>] [--translate]
```

### Options

| Flag                  | Description                                              |
|-----------------------|----------------------------------------------------------|
| `--powershell`        | Translate to PowerShell (default)                        |
| `--cmd`               | Translate to Windows CMD                                 |
| `--target <shell>`    | Explicitly set target: `cmd` or `powershell`             |
| `--translate`         | Print each translated command before executing it        |
| `--disable-translate` | Suppress translation output (cancels `--translate`)      |

### Examples

```bash
# Start with PowerShell target (default)
python -m linuxConverter

# Start targeting CMD
python -m linuxConverter --cmd

# Show the translated command before running it
python -m linuxConverter --translate

# Combine: CMD target with translation output
python -m linuxConverter --cmd --translate
```

---

## REPL Usage

Once running, type Linux commands at the prompt:

```
linuxConverter(powershell)
C:/Users/you/project> ls -la
linuxConverter(powershell)
C:/Users/you/project> cat README.md | grep install
linuxConverter(powershell)
C:/Users/you/project> ls | grep .py | head -5
linuxConverter(powershell)
C:/Users/you/project> find . -name "*.py"
linuxConverter(powershell)
C:/Users/you/project> wc -l main.py
linuxConverter(powershell)
C:/Users/you/project> ps aux | grep python
linuxConverter(powershell)
C:/Users/you/project> cd ..
linuxConverter(powershell)
C:/Users/you> mkdir new-folder
```

### In-session commands

| Input                 | Action                                 |
|-----------------------|----------------------------------------|
| `--translate`         | Enable translation output              |
| `--disable-translate` | Disable translation output             |
| `help`                | Show help message                      |
| `exit`                | Quit                                   |
| `Ctrl+C`              | Cancel current input, return to prompt |
| `Ctrl+D` / EOF        | Exit                                   |

### Tab Completion

Press `Tab` after any command to autocomplete file and directory names relative to your current working directory.

- One match: inserted automatically inline.
- Multiple matches: printed in columns and the prompt resets so you can continue typing.

Commands like `cd`, `mkdir`, `find`, `du`, and `ln` complete **directories only**. All other commands complete both files and directories.

---

## Project Structure

```
winux/
├── linuxConverter/
│   ├── __init__.py        # Public API exports
│   ├── __main__.py        # Entry point (python -m linuxConverter)
│   ├── cli.py             # Argument parsing and REPL loop
│   ├── translator.py      # Command translation logic (PowerShell & CMD)
│   ├── pipeline_parser.py # Splits piped input into segments
│   ├── command_parser.py  # Tokenizes individual command segments
│   ├── executor.py        # Runs translated commands via subprocess
│   ├── shell_state.py     # Directory resolution and prompt formatting
│   └── prompting.py       # Tab completion and key bindings
└── tests/
    └── __init__.py
```

---

## License

MIT
