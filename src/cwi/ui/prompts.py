"""Prompt abstraction. Every question has a stable `key` so flows can be scripted and tested."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from cwi.domain.errors import UserCancelled


@dataclass
class Option:
    value: Any
    label: str
    checked: bool = False
    separator: bool = False  # visual heading inside a list; never selectable


def heading(label: str) -> Option:
    return Option(value=None, label=label, separator=True)


class Prompter(Protocol):
    interactive: bool

    def select(self, key: str, message: str, options: list[Option], default: Any = None) -> Any: ...

    def checkbox(self, key: str, message: str, options: list[Option]) -> list[Any]: ...

    def confirm(self, key: str, message: str, default: bool = True) -> bool: ...

    def text(self, key: str, message: str, default: str = "") -> str: ...


def _default_select(options: list[Option], default: Any) -> Any:
    if default is not None:
        return default
    return options[0].value if options else None


class AutoPrompter:
    """Accepts every default. Used by --yes, --dry-run and non-interactive terminals."""

    interactive = False

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self.overrides = overrides or {}
        self.asked: list[str] = []

    def select(self, key: str, message: str, options: list[Option], default: Any = None) -> Any:
        self.asked.append(key)
        return self.overrides.get(key, _default_select(options, default))

    def checkbox(self, key: str, message: str, options: list[Option]) -> list[Any]:
        self.asked.append(key)
        return self.overrides.get(key, [o.value for o in options if o.checked and not o.separator])

    def confirm(self, key: str, message: str, default: bool = True) -> bool:
        self.asked.append(key)
        return self.overrides.get(key, default)

    def text(self, key: str, message: str, default: str = "") -> str:
        self.asked.append(key)
        return self.overrides.get(key, default)


class ScriptedPrompter(AutoPrompter):
    """Answers from a script: key -> answer, or key -> list of answers consumed in order."""

    def __init__(self, answers: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.answers = dict(answers or {})

    def _take(self, key: str, fallback: Any) -> Any:
        if key not in self.answers:
            return fallback
        value = self.answers[key]
        if isinstance(value, Queue):
            return value.items.pop(0) if value.items else fallback
        return value

    def select(self, key: str, message: str, options: list[Option], default: Any = None) -> Any:
        self.asked.append(key)
        return self._take(key, _default_select(options, default))

    def checkbox(self, key: str, message: str, options: list[Option]) -> list[Any]:
        self.asked.append(key)
        return self._take(key, [o.value for o in options if o.checked and not o.separator])

    def confirm(self, key: str, message: str, default: bool = True) -> bool:
        self.asked.append(key)
        return self._take(key, default)

    def text(self, key: str, message: str, default: str = "") -> str:
        self.asked.append(key)
        return self._take(key, default)


@dataclass
class Queue:
    """Sequence of answers for a prompt key that is asked several times."""

    items: list[Any]


class InquirerPrompter:
    """Interactive terminal prompts backed by InquirerPy."""

    interactive = True

    def __init__(self) -> None:
        from InquirerPy import inquirer  # imported lazily: only needed on a real TTY

        self._inquirer = inquirer

    @staticmethod
    def _run(prompt: Any) -> Any:
        try:
            return prompt.execute()
        except KeyboardInterrupt as exc:
            raise UserCancelled("Cancelled. No changes were made.") from exc

    def select(self, key: str, message: str, options: list[Option], default: Any = None) -> Any:
        from InquirerPy.base.control import Choice

        choices = [Choice(value=o.value, name=o.label) for o in options]
        return self._run(
            self._inquirer.select(message=message, choices=choices, default=default, mandatory=True)
        )

    def checkbox(self, key: str, message: str, options: list[Option]) -> list[Any]:
        from InquirerPy.base.control import Choice
        from InquirerPy.separator import Separator

        if not any(not o.separator for o in options):
            return []
        choices = [
            Separator(o.label)
            if o.separator
            else Choice(value=o.value, name=o.label, enabled=o.checked)
            for o in options
        ]
        return self._run(
            self._inquirer.checkbox(
                message=message,
                choices=choices,
                instruction="(space: toggle, a: all, i: invert, enter: confirm)",
                cycle=True,
                transformer=lambda result: f"{len(result)} selected",
            )
        )

    def confirm(self, key: str, message: str, default: bool = True) -> bool:
        return bool(self._run(self._inquirer.confirm(message=message, default=default)))

    def text(self, key: str, message: str, default: str = "") -> str:
        return str(self._run(self._inquirer.text(message=message, default=default)))
