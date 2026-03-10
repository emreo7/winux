from dataclasses import dataclass
from typing import Callable, Dict, List
import shlex

from .models import ParsedCommand, Pipeline, TranslationResult


def normalize_target(target: str) -> str:
    normalized = target.lower()
    if normalized in {"cmd", "powershell"}:
        return normalized
    raise ValueError(f"Unsupported target '{target}'")


@dataclass
class SegmentTranslation:
    text: str
    warnings: List[str]
    unsupported: List[str]
    pipeline_compatible: bool


class Translator:
    DEFAULT_COUNT = 10

    def __init__(self, target: str):
        self.target = normalize_target(target)

    def translate(self, pipeline: Pipeline) -> TranslationResult:
        if self.target == "powershell":
            return self._translate_powershell(pipeline)
        return self._translate_cmd(pipeline)

    def _translate_powershell(self, pipeline: Pipeline) -> TranslationResult:
        warnings: List[str] = []
        unsupported: List[str] = []
        translated_segments: List[str] = []
        in_pipeline = len(pipeline.segments) > 1

        for segment in pipeline.segments:
            segment_result = self._translate_segment_powershell(segment, in_pipeline)
            warnings.extend(segment_result.warnings)
            unsupported.extend(segment_result.unsupported)
            translated_segments.append(segment_result.text)

        translated = " | ".join(translated_segments)
        return TranslationResult(translated=translated, warnings=warnings, unsupported=unsupported)

    def _translate_cmd(self, pipeline: Pipeline) -> TranslationResult:
        warnings: List[str] = []
        unsupported: List[str] = []
        segment_results: List[SegmentTranslation] = []
        in_pipeline = len(pipeline.segments) > 1

        for segment in pipeline.segments:
            segment_result = self._translate_segment_cmd(segment, in_pipeline)
            warnings.extend(segment_result.warnings)
            unsupported.extend(segment_result.unsupported)
            segment_results.append(segment_result)

        if not segment_results:
            return TranslationResult(translated="", warnings=warnings, unsupported=unsupported)

        if len(segment_results) == 1:
            translated = segment_results[0].text
            return TranslationResult(translated=translated, warnings=warnings, unsupported=unsupported)

        all_compatible = all(result.pipeline_compatible for result in segment_results)
        if all_compatible:
            translated = " | ".join(result.text for result in segment_results if result.text)
            return TranslationResult(translated=translated, warnings=warnings, unsupported=unsupported)

        translated = segment_results[0].text
        ps_suggestion = Translator("powershell")._translate_powershell(pipeline).translated
        if ps_suggestion:
            warnings.append(f"Suggested PowerShell equivalent: {ps_suggestion}")
        return TranslationResult(translated=translated, warnings=warnings, unsupported=unsupported)

    # ------------------------------------------------------------------
    # PowerShell translation
    # ------------------------------------------------------------------

    def _translate_segment_powershell(self, command: ParsedCommand, in_pipeline: bool) -> SegmentTranslation:
        warnings: List[str] = []
        unsupported: List[str] = []
        name = command.command.lower()

        pipe_only = {"grep", "head", "tail", "sort", "uniq", "wc", "sed", "awk"}
        if name in pipe_only and not in_pipeline:
            warnings.append(f"'{name}' is most useful inside pipelines")

        translators: Dict[str, Callable[[ParsedCommand], str]] = {
            # --- filesystem ---
            "pwd":      lambda cmd: "Get-Location",
            "ls":       lambda cmd: _ps_ls(cmd),
            "cd":       lambda cmd: _with_args("Set-Location", cmd.args),
            "mkdir":    lambda cmd: _ps_mkdir(cmd),
            "touch":    lambda cmd: _ps_touch(cmd),
            "rm":       lambda cmd: _ps_rm(cmd),
            "cp":       lambda cmd: _ps_cp(cmd),
            "mv":       lambda cmd: _with_args("Move-Item", cmd.args),
            "ln":       lambda cmd: _ps_ln(cmd),
            "find":     lambda cmd: _ps_find(cmd),
            "du":       lambda cmd: _ps_du(cmd),
            "df":       lambda cmd: "Get-PSDrive -PSProvider FileSystem",
            "chmod":    lambda cmd: _ps_unsupported(cmd, warnings, unsupported, "chmod has no direct PowerShell equivalent; use Set-Acl for ACL management"),
            "chown":    lambda cmd: _ps_unsupported(cmd, warnings, unsupported, "chown has no direct PowerShell equivalent; use Set-Acl for ownership"),
            # --- text / content ---
            "cat":      lambda cmd: _ps_cat(cmd),
            "echo":     lambda cmd: _echo(cmd),
            "grep":     lambda cmd: _ps_grep(cmd),
            "head":     lambda cmd: f"Select-Object -First {self._extract_count(cmd)}",
            "tail":     lambda cmd: f"Select-Object -Last {self._extract_count(cmd)}",
            "sort":     lambda cmd: _ps_sort(cmd),
            "uniq":     lambda cmd: "Select-Object -Unique",
            "wc":       lambda cmd: _ps_wc(cmd),
            "diff":     lambda cmd: _ps_diff(cmd),
            "sed":      lambda cmd: _ps_sed(cmd),
            "awk":      lambda cmd: _ps_unsupported(cmd, warnings, unsupported, "awk has no direct PowerShell equivalent; consider using Select-String or custom scripts"),
            # --- system ---
            "ps":       lambda cmd: _ps_ps(cmd),
            "kill":     lambda cmd: _ps_kill(cmd),
            "sleep":    lambda cmd: _with_args("Start-Sleep", cmd.args),
            "whoami":   lambda cmd: "whoami",
            "date":     lambda cmd: "Get-Date",
            "clear":    lambda cmd: "Clear-Host",
            "history":  lambda cmd: "Get-History",
            "env":      lambda cmd: "Get-ChildItem Env:",
            "export":   lambda cmd: _ps_export(cmd),
            "which":    lambda cmd: _ps_which(cmd),
            "man":      lambda cmd: _ps_man(cmd),
            "uname":    lambda cmd: _ps_uname(cmd),
            "uptime":   lambda cmd: "(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime",
            "free":     lambda cmd: "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory",
            # --- archive ---
            "tar":      lambda cmd: _ps_tar(cmd),
            "zip":      lambda cmd: _ps_zip(cmd),
            "unzip":    lambda cmd: _ps_unzip(cmd),
            # --- network ---
            "ping":     lambda cmd: _with_args("ping", cmd.args),
            "curl":     lambda cmd: _ps_curl(cmd),
            "wget":     lambda cmd: _ps_wget(cmd),
            "ssh":      lambda cmd: _passthrough(cmd),
            "scp":      lambda cmd: _passthrough(cmd),
            "ifconfig": lambda cmd: "Get-NetIPAddress",
            "ip":       lambda cmd: _ps_ip(cmd),
            "netstat":  lambda cmd: "Get-NetTCPConnection",
            # --- git (passthrough) ---
            "git":      lambda cmd: _git_passthrough(cmd),
            # --- package managers (passthrough) ---
            "npm":      lambda cmd: _passthrough(cmd),
            "pip":      lambda cmd: _passthrough(cmd),
            "python":   lambda cmd: _passthrough(cmd),
            "python3":  lambda cmd: _passthrough(cmd),
            "node":     lambda cmd: _passthrough(cmd),
        }

        if name in translators:
            text = translators[name](command).strip()
        else:
            warnings.append(f"Unsupported command '{command.command}' — passing through as-is")
            unsupported.append(command.command)
            text = command.raw

        return SegmentTranslation(
            text=text,
            warnings=warnings,
            unsupported=unsupported,
            pipeline_compatible=True,
        )

    # ------------------------------------------------------------------
    # CMD translation
    # ------------------------------------------------------------------

    def _translate_segment_cmd(self, command: ParsedCommand, in_pipeline: bool) -> SegmentTranslation:
        warnings: List[str] = []
        unsupported: List[str] = []
        name = command.command.lower()

        # Commands with no useful CMD equivalent — suggest PowerShell
        ps_only = {"find", "du", "df", "ps", "kill", "env", "export", "which",
                   "man", "uname", "uptime", "free", "tar", "zip", "unzip",
                   "wget", "curl", "netstat", "diff", "chmod", "chown",
                   "sed", "awk", "uniq", "ln"}
        if name in ps_only:
            warnings.append(f"'{name}' is not natively supported in CMD — consider using PowerShell (--powershell flag)")
            unsupported.append(name)
            ps_suggestion = Translator("powershell")._translate_segment_powershell(command, in_pipeline).text
            if ps_suggestion and ps_suggestion != command.raw:
                warnings.append(f"PowerShell equivalent: {ps_suggestion}")
            return SegmentTranslation(text=command.raw, warnings=warnings, unsupported=unsupported, pipeline_compatible=False)

        translators: Dict[str, Callable[[ParsedCommand], str]] = {
            # --- filesystem ---
            "pwd":      lambda cmd: "cd",
            "ls":       lambda cmd: _cmd_ls(cmd),
            "cd":       lambda cmd: _with_args("cd", cmd.args),
            "mkdir":    lambda cmd: _cmd_mkdir(cmd),
            "touch":    lambda cmd: _cmd_touch(cmd),
            "rm":       lambda cmd: _cmd_rm(cmd),
            "cp":       lambda cmd: _cmd_cp(cmd),
            "mv":       lambda cmd: _with_args("move", cmd.args),
            # --- text / content ---
            "cat":      lambda cmd: _cmd_cat(cmd),
            "echo":     lambda cmd: _echo(cmd),
            "grep":     lambda cmd: _cmd_grep(cmd, in_pipeline, warnings, unsupported),
            "sort":     lambda cmd: _cmd_sort(cmd),
            "wc":       lambda cmd: _cmd_wc_warn(cmd, warnings, unsupported),
            # --- system ---
            "whoami":   lambda cmd: "whoami",
            "date":     lambda cmd: "date /t",
            "clear":    lambda cmd: "cls",
            "history":  lambda cmd: "doskey /history",
            "sleep":    lambda cmd: _cmd_sleep(cmd),
            "ping":     lambda cmd: _with_args("ping", cmd.args),
            "ssh":      lambda cmd: _passthrough(cmd),
            "scp":      lambda cmd: _passthrough(cmd),
            "ifconfig": lambda cmd: "ipconfig",
            "ip":       lambda cmd: "ipconfig",
            "netstat":  lambda cmd: "netstat",
            # --- git / tools (passthrough) ---
            "git":      lambda cmd: _git_passthrough(cmd),
            "npm":      lambda cmd: _passthrough(cmd),
            "pip":      lambda cmd: _passthrough(cmd),
            "python":   lambda cmd: _passthrough(cmd),
            "python3":  lambda cmd: _passthrough(cmd),
            "node":     lambda cmd: _passthrough(cmd),
        }

        # head/tail: no CMD equivalent
        if name in {"head", "tail"}:
            warnings.append(f"CMD does not support '{name}' — use PowerShell instead")
            unsupported.append(name)
            return SegmentTranslation(text=command.raw, warnings=warnings, unsupported=unsupported, pipeline_compatible=False)

        if name in translators:
            translated = translators[name](command).strip()
            compatible = name not in {"wc"}
            return SegmentTranslation(text=translated, warnings=warnings, unsupported=unsupported, pipeline_compatible=compatible)

        warnings.append(f"Unsupported command '{command.command}' for CMD — passing through as-is")
        unsupported.append(command.command)
        return SegmentTranslation(text=command.raw, warnings=warnings, unsupported=unsupported, pipeline_compatible=False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_pattern(self, command: ParsedCommand) -> str:
        non_flag_args = [a for a in command.args if not a.startswith("-")]
        if non_flag_args:
            return non_flag_args[0]
        if command.flags:
            return command.flags[-1]
        return ""

    def _extract_count(self, command: ParsedCommand) -> int:
        for flag in command.flags:
            digits = flag.lstrip("-")
            if digits.isdigit():
                return int(digits)
        for value in command.args:
            if value.lstrip("-").isdigit():
                return int(value.lstrip("-"))
        return self.DEFAULT_COUNT


# ======================================================================
# PowerShell helpers
# ======================================================================

def _ps_ls(cmd: ParsedCommand) -> str:
    parts = ["Get-ChildItem"]
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    if "a" in flags or "la" in flags or "al" in flags:
        parts.append("-Force")
    if "r" in flags or "R" in flags:
        parts.append("-Recurse")
    if cmd.args:
        parts.append(_quote_args(cmd.args))
    return " ".join(parts)


def _ps_mkdir(cmd: ParsedCommand) -> str:
    # -p / --parents: PowerShell New-Item creates intermediate dirs by default
    args = [a for a in cmd.args if not a.startswith("-")]
    if not args:
        return "New-Item -ItemType Directory"
    parts = []
    for path in args:
        parts.append(f'New-Item -ItemType Directory -Path "{path}" -Force')
    return " ; ".join(parts)


def _ps_touch(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if not args:
        return "New-Item -ItemType File -Force"
    parts = []
    for path in args:
        parts.append(f'New-Item -ItemType File -Path "{path}" -Force')
    return " ; ".join(parts)


def _ps_rm(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    parts = ["Remove-Item"]
    if "r" in flags or "rf" in flags or "fr" in flags or "recursive" in flags:
        parts.append("-Recurse")
    parts.append("-Force")
    if cmd.args:
        parts.append(_quote_args(cmd.args))
    return " ".join(parts)


def _ps_cp(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    parts = ["Copy-Item"]
    if "r" in flags or "recursive" in flags:
        parts.append("-Recurse")
    if cmd.args:
        parts.append(_quote_args(cmd.args))
    return " ".join(parts)


def _ps_cat(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    parts = ["Get-Content"]
    if cmd.args:
        parts.append(_quote_args([a for a in cmd.args if not a.startswith("-")]))
    if "n" in flags:
        # number lines
        return " ".join(parts) + " | Select-String '.' | ForEach-Object { $_.LineNumber.ToString().PadLeft(6) + \"`t\" + $_.Line }"
    return " ".join(parts)


def _ps_grep(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    pattern = args[0] if args else ""
    files = args[1:] if len(args) > 1 else []

    not_match = "-NotMatch" if "v" in flags else ""
    case_sensitive = "-CaseSensitive" if "s" in flags else ""

    post: List[str] = []
    if "l" in flags:
        post.append("| Select-Object -ExpandProperty Path -Unique")
    elif "c" in flags:
        post.append("| Measure-Object | Select-Object -ExpandProperty Count")
    elif "n" in flags:
        post.append('| ForEach-Object { $_.LineNumber.ToString() + ":" + $_.Line }')

    if "r" in flags or "R" in flags:
        # Recursive: pipe Get-ChildItem into Select-String, skip __pycache__ and .pyc
        search_path = _quote_args(files) if files else "."
        base = f'Get-ChildItem -Path {search_path} -Recurse -File | Where-Object {{ $_.FullName -notlike "*__pycache__*" -and $_.FullName -notlike "*\\.venv\\*" -and $_.Extension -ne ".pyc" }} | Select-String'
        opts = " ".join(p for p in [not_match, case_sensitive] if p)
        pat = f'"{pattern}"' if pattern else ""
        parts = [p for p in [base, opts, pat] if p]
        return " ".join(parts + post)
    else:
        base = "Select-String"
        opts = " ".join(p for p in [not_match, case_sensitive] if p)
        pat = f'"{pattern}"' if pattern else ""
        file_arg = f"-Path {_quote_args(files)}" if files else ""
        parts = [p for p in [base, opts, pat, file_arg] if p]
        return " ".join(parts + post)


def _ps_sort(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    parts = ["Sort-Object"]
    if "r" in flags or "reverse" in flags:
        parts.append("-Descending")
    if "u" in flags or "unique" in flags:
        parts.append("-Unique")
    if cmd.args:
        parts.append(_quote_args([a for a in cmd.args if not a.startswith("-")]))
    return " ".join(parts)


def _ps_wc(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    if "l" in flags:
        if args:
            return f'(Get-Content "{args[0]}").Count'
        return "Measure-Object -Line"
    if "w" in flags:
        if args:
            return f'((Get-Content "{args[0]}") -join " ").Split() | Measure-Object | Select-Object -ExpandProperty Count'
        return "Measure-Object -Word"
    if "c" in flags:
        if args:
            return f'(Get-Content -Raw "{args[0]}").Length'
        return "Measure-Object -Character"
    # default: lines
    if args:
        return f'(Get-Content "{args[0]}").Count'
    return "Measure-Object -Line"


def _ps_diff(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if len(args) >= 2:
        return f'Compare-Object (Get-Content "{args[0]}") (Get-Content "{args[1]}")'
    return "Compare-Object"


def _ps_sed(cmd: ParsedCommand) -> str:
    # Best effort: translate simple s/old/new/ substitution
    args = [a for a in cmd.args if not a.startswith("-")]
    if args and args[0].startswith("s/"):
        try:
            parts = args[0].split("/")
            if len(parts) >= 3:
                old, new = parts[1], parts[2]
                flags_part = parts[3] if len(parts) > 3 else ""
                files = args[1:] if len(args) > 1 else []
                if files:
                    return f'(Get-Content "{files[0]}") -replace "{old}", "{new}" | Set-Content "{files[0]}"'
                return f'ForEach-Object {{ $_ -replace "{old}", "{new}" }}'
        except Exception:
            pass
    return f"ForEach-Object {{ $_ }}"


def _ps_ps(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    if "a" in flags or "e" in flags or "aux" in flags:
        return "Get-Process"
    if "u" in flags:
        return "Get-Process | Select-Object Name,Id,CPU,WorkingSet"
    return "Get-Process"


def _ps_kill(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    force = "9" in flags or "sigkill" in flags or "kill" in flags
    if not args:
        return "Stop-Process"
    pid_or_name = args[0]
    if pid_or_name.isdigit():
        base = f"Stop-Process -Id {pid_or_name}"
    else:
        base = f'Stop-Process -Name "{pid_or_name}"'
    return base + (" -Force" if force else "")


def _ps_export(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if args and "=" in args[0]:
        key, _, val = args[0].partition("=")
        return f'$env:{key} = "{val}"'
    return f"$env:{' '.join(args)}"


def _ps_which(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if args:
        return f'(Get-Command "{args[0]}").Source'
    return "Get-Command"


def _ps_man(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if args:
        return f"Get-Help {args[0]} -Full"
    return "Get-Help"


def _ps_uname(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    if "a" in flags:
        return "[System.Environment]::OSVersion | Select-Object -ExpandProperty VersionString"
    return "[System.Environment]::OSVersion.Platform"


def _ps_find(cmd: ParsedCommand) -> str:
    import shlex as _shlex
    # Re-tokenize from raw to preserve flag+value pairs that command_parser splits apart
    tokens = _shlex.split(cmd.raw)[1:]  # drop "find"

    path = "."
    name_pattern = None
    type_filter = None
    max_depth = None

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith("-"):
            path = tok
            i += 1
            continue
        key = tok.lstrip("-").lower()
        if key == "name" and i + 1 < len(tokens):
            name_pattern = tokens[i + 1]
            i += 2
            continue
        if key == "type" and i + 1 < len(tokens):
            type_filter = tokens[i + 1]
            i += 2
            continue
        if key == "maxdepth" and i + 1 < len(tokens):
            max_depth = tokens[i + 1]
            i += 2
            continue
        i += 1

    gci = f'Get-ChildItem -Path "{path}" -Recurse'
    if name_pattern:
        gci += f' -Filter "{name_pattern}"'

    filters = [
        '$_.FullName -notlike "*\\.venv\\*"',
        '$_.FullName -notlike "*__pycache__*"',
    ]
    if type_filter == "d":
        filters.append("$_.PSIsContainer")
    elif type_filter == "f":
        filters.append("-not $_.PSIsContainer")
    if max_depth:
        filters.append(f"$_.FullName.Split('\\').Count -le ($pwd.Path.Split('\\').Count + {max_depth})")

    where = " -and ".join(filters)
    return f"{gci} | Where-Object {{ {where} }} | Select-Object -ExpandProperty FullName"


def _ps_du(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    path = f'"{args[0]}"' if args else "."
    if "s" in flags or "sh" in flags:
        return f"(Get-ChildItem {path} -Recurse | Measure-Object -Property Length -Sum).Sum"
    return f"Get-ChildItem {path} -Recurse | Measure-Object -Property Length -Sum"


def _ps_ln(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    if len(args) < 2:
        return "New-Item -ItemType SymbolicLink"
    target, link = args[0], args[1]
    if "s" in flags:
        return f'New-Item -ItemType SymbolicLink -Path "{link}" -Target "{target}"'
    return f'New-Item -ItemType HardLink -Path "{link}" -Target "{target}"'


def _ps_tar(cmd: ParsedCommand) -> str:
    flags_raw = "".join(f.lstrip("-") for f in cmd.flags)
    flags = set(flags_raw.lower())
    args = [a for a in cmd.args if not a.startswith("-")]

    if "c" in flags:
        archive = args[0] if args else "archive.tar.gz"
        sources = args[1:] if len(args) > 1 else ["."]
        src_str = ", ".join(f'"{s}"' for s in sources)
        return f'Compress-Archive -Path {src_str} -DestinationPath "{archive}"'
    if "x" in flags:
        archive = args[0] if args else "archive.tar.gz"
        dest = args[1] if len(args) > 1 else "."
        return f'Expand-Archive -Path "{archive}" -DestinationPath "{dest}"'
    if "t" in flags:
        archive = args[0] if args else "archive.tar.gz"
        return f'(Get-ChildItem (Expand-Archive "{archive}" -PassThru)).Name'
    return f'Compress-Archive {_quote_args(args)}'


def _ps_zip(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if len(args) >= 2:
        return f'Compress-Archive -Path "{args[1]}" -DestinationPath "{args[0]}"'
    return f'Compress-Archive {_quote_args(args)}'


def _ps_unzip(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    dest = args[1] if len(args) > 1 else "."
    archive = args[0] if args else "archive.zip"
    return f'Expand-Archive -Path "{archive}" -DestinationPath "{dest}"'


def _ps_curl(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    url = args[0] if args else ""
    output = None

    # find -o / --output
    for i, f in enumerate(cmd.flags):
        if f in {"-o", "--output"} and i + 1 < len(cmd.flags):
            output = cmd.flags[i + 1]
        elif f in {"-o", "--output"} and cmd.args:
            output = cmd.args[-1]

    if output:
        return f'Invoke-WebRequest -Uri "{url}" -OutFile "{output}"'
    if "i" in flags or "head" in flags:
        return f'Invoke-WebRequest -Uri "{url}" | Select-Object StatusCode,Headers'
    return f'Invoke-WebRequest -Uri "{url}" | Select-Object -ExpandProperty Content'


def _ps_wget(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    url = args[0] if args else ""
    # -O flag
    output = None
    for i, f in enumerate(cmd.flags):
        if f == "-O" and i + 1 < len(cmd.flags):
            output = cmd.flags[i + 1]
    if output:
        return f'Invoke-WebRequest -Uri "{url}" -OutFile "{output}"'
    return f'Invoke-WebRequest -Uri "{url}" -OutFile "{url.split("/")[-1] or "output"}"'


def _ps_ip(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    sub = args[0].lower() if args else ""
    if sub in {"addr", "address", "a"}:
        return "Get-NetIPAddress"
    if sub in {"link", "l"}:
        return "Get-NetAdapter"
    if sub in {"route", "r"}:
        return "Get-NetRoute"
    return "Get-NetIPConfiguration"


def _ps_unsupported(cmd: ParsedCommand, warnings: List[str], unsupported: List[str], msg: str) -> str:
    warnings.append(msg)
    unsupported.append(cmd.command)
    return cmd.raw


# ======================================================================
# CMD helpers
# ======================================================================

def _cmd_ls(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    parts = ["dir"]
    if "a" in flags or "la" in flags or "al" in flags:
        parts.append("/a")
    if "s" in flags or "r" in flags or "R" in flags:
        parts.append("/s")
    if cmd.args:
        parts.append(_quote_args([a for a in cmd.args if not a.startswith("-")]))
    return " ".join(parts)


def _cmd_mkdir(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if not args:
        return "mkdir"
    return "mkdir " + _quote_args(args)


def _cmd_touch(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if not args:
        return "type NUL > nul"
    parts = []
    for path in args:
        parts.append(f'type NUL > "{path}"')
    return " & ".join(parts)


def _cmd_rm(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    is_recursive = "r" in flags or "rf" in flags or "fr" in flags or "recursive" in flags

    if is_recursive:
        if args:
            return f'rmdir /s /q "{args[0]}"'
        return "rmdir /s /q"
    if args:
        return "del /f " + _quote_args(args)
    return "del /f"


def _cmd_cp(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    is_recursive = "r" in flags or "recursive" in flags

    if is_recursive:
        if len(args) >= 2:
            return f'xcopy "{args[0]}" "{args[1]}" /e /i /h'
        return "xcopy /e /i /h"
    return "copy " + _quote_args(args)


def _cmd_cat(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if not args:
        return "type"
    return "type " + _quote_args(args)


def _cmd_grep(cmd: ParsedCommand, in_pipeline: bool, warnings: List[str], unsupported: List[str]) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    args = [a for a in cmd.args if not a.startswith("-")]
    pattern = args[0] if args else ""
    files = args[1:] if len(args) > 1 else []

    if "r" in flags or "R" in flags:
        warnings.append("'grep -r' not natively supported in CMD; consider PowerShell (findstr /s)")
    if "i" in flags:
        base = f'findstr /i "{pattern}"'
    else:
        base = f'findstr "{pattern}"'
    if files:
        base += " " + _quote_args(files)
    return base


def _cmd_sort(cmd: ParsedCommand) -> str:
    flags = {f.lstrip("-").lower() for f in cmd.flags}
    parts = ["sort"]
    if "r" in flags or "reverse" in flags:
        parts.append("/r")
    if cmd.args:
        args = [a for a in cmd.args if not a.startswith("-")]
        if args:
            parts.append(_quote_args(args))
    return " ".join(parts)


def _cmd_wc_warn(cmd: ParsedCommand, warnings: List[str], unsupported: List[str]) -> str:
    warnings.append("'wc' is not available in CMD; consider PowerShell for line/word/char counting")
    unsupported.append("wc")
    return cmd.raw


def _cmd_sleep(cmd: ParsedCommand) -> str:
    args = [a for a in cmd.args if not a.startswith("-")]
    if args and args[0].isdigit():
        return f"timeout /t {args[0]} /nobreak"
    return "timeout /t 1 /nobreak"


# ======================================================================
# Shared helpers
# ======================================================================

def _with_args(prefix: str, args: List[str], trailing: str = "") -> str:
    clean_args = [a for a in args if not a.startswith("-")]
    args_section = " ".join(clean_args).strip()
    if args_section:
        return f"{prefix} {args_section}{trailing}"
    return f"{prefix}{trailing}"


def _echo(cmd: ParsedCommand) -> str:
    text = " ".join(cmd.flags + cmd.args).strip()
    return f"echo {text}".strip()


def _quote_args(args: List[str]) -> str:
    parts = []
    for a in args:
        if " " in a and not (a.startswith('"') and a.endswith('"')):
            parts.append(f'"{a}"')
        else:
            parts.append(a)
    return " ".join(parts)


def _passthrough(cmd: ParsedCommand) -> str:
    return cmd.raw


def _git_passthrough(cmd: ParsedCommand) -> str:
    tokens = shlex.split(cmd.raw)
    if len(tokens) <= 1:
        return "git"
    return "git " + " ".join(tokens[1:])


