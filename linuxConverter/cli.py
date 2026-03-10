import argparse
import os
import sys
from typing import Optional

from .pipeline_parser import parse_pipeline
from .translator import Translator
from .executor import execute_translation
from .shell_state import resolve_directory, format_prompt_path
from .prompting import create_prompt_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linuxConverter",
        description="Translate Linux-style commands and pipelines to Windows CMD or PowerShell equivalents.",
    )
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--cmd",
        dest="target",
        action="store_const",
        const="cmd",
        help="Translate to Windows CMD.",
    )
    target_group.add_argument(
        "--powershell",
        dest="target",
        action="store_const",
        const="powershell",
        help="Translate to Windows PowerShell.",
    )
    target_group.add_argument(
        "--target",
        choices=["cmd", "powershell"],
        help="Explicitly set translation target.",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Show translated commands before executing them.",
    )
    parser.add_argument(
        "--disable-translate",
        action="store_true",
        help="Do not show translated commands before executing them.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    target = args.target or "powershell"
    translator = Translator(target)
    show_translation = args.translate and not args.disable_translate
    repl(translator, show_translation=show_translation)


def repl(translator: Translator, show_translation: bool = False) -> None:
    help_text = (
        "Type Linux commands or pipelines for translation.\n"
        "- Empty input: no action\n"
        "- exit: quit\n"
        "- help: show this message\n"
        "- Ctrl+C: return to prompt\n"
        "- Ctrl+D / EOF: exit"
    )
    cwd = os.getcwd()

    session = create_prompt_session(lambda: cwd)

    while True:
        try:
            prompt = f"linuxConverter({translator.target})\n{format_prompt_path(cwd)}> "
            raw_input = session.prompt(prompt)
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue

        command_line = raw_input.strip()
        if not command_line:
            continue

        if command_line in {"linuxConverter --translate", "--translate"}:
            show_translation = True
            print("Translation output enabled.")
            continue
        if command_line in {"linuxConverter --disable translate", "--disable translate", "--disable-translate", "linuxConverter --disable-translate"}:
            show_translation = False
            print("Translation output disabled.")
            continue

        if command_line == "exit":
            break

        if command_line.startswith("help"):
            print(help_text)
            continue

        pipeline = parse_pipeline(command_line)
        result = translator.translate(pipeline)

        is_cd = len(pipeline.segments) == 1 and pipeline.segments[0].command.lower() == "cd"

        if result.translated and show_translation:
            print(result.translated)

        if result.translated:
            if is_cd:
                new_cwd, cd_error = resolve_directory(cwd, pipeline.segments[0].args)
                if cd_error:
                    print(cd_error)
                else:
                    os.chdir(new_cwd)
                    cwd = new_cwd
            else:
                exec_result = execute_translation(translator.target, result.translated, cwd=cwd)
                if exec_result.stdout:
                    print(exec_result.stdout, end="" if exec_result.stdout.endswith("\n") else "\n")
                if exec_result.stderr:
                    print(exec_result.stderr, file=sys.stderr, end="" if exec_result.stderr.endswith("\n") else "\n")
                if exec_result.returncode != 0:
                    print(f"Command exited with code {exec_result.returncode}")

        for warning in result.warnings:
            print(f"Warning: {warning}")

        if is_cd:
            continue
