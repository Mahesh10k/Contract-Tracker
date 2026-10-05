"""The prompt registry loader (prompt-registry): prompts live in prompts/<name>/v<N>.md.

Frontmatter is TOML between `+++` lines (stdlib tomllib, no new dependency).
`render` validates the variables before any model call, substitutes
`{{name}}` only (JSON braces in the body are untouched) and escapes a
closing delimiter tag found inside a value, so contract text cannot close
its own `<contract>` block.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class PromptError(ValueError):
    """A prompt is missing or a variable is missing, unknown or too long."""


@dataclass(frozen=True)
class Variable:
    """One declared variable: its name, whether it is required and its length limit."""

    name: str
    required: bool
    max_chars: int


@dataclass(frozen=True)
class Prompt:
    """One prompt version: its frontmatter and its body."""

    name: str
    version: int
    status: str
    model: str
    effort: str
    max_tokens: int
    owner: str
    eval_set: str
    variables: tuple[Variable, ...]
    body: str


def load(name: str, version: int) -> Prompt:
    """Read prompts/<name>/v<version>.md."""
    path = PROMPTS_DIR / name / f"v{version}.md"
    if not path.exists():
        raise PromptError(f"no prompt {name} v{version} at {path}")
    text = path.read_text()
    if not text.startswith("+++\n"):
        raise PromptError(f"{path}: frontmatter must start with +++")
    front, body = text[4:].split("\n+++\n", 1)
    meta = tomllib.loads(front)
    return Prompt(
        name=str(meta["name"]),
        version=int(meta["version"]),
        status=str(meta["status"]),
        model=str(meta["model"]),
        effort=str(meta["effort"]),
        max_tokens=int(meta["max_tokens"]),
        owner=str(meta["owner"]),
        eval_set=str(meta["eval_set"]),
        variables=tuple(
            Variable(
                name=str(v["name"]), required=bool(v["required"]), max_chars=int(v["max_chars"])
            )
            for v in meta["variables"]
        ),
        body=body.lstrip("\n"),
    )


def render(prompt: Prompt, values: dict[str, str]) -> str:
    """The prompt body with every variable substituted, after validating them all."""
    declared = {v.name: v for v in prompt.variables}
    for key in values:
        if key not in declared:
            raise PromptError(f"unknown variable: {key}")
    for var in prompt.variables:
        if var.required and var.name not in values:
            raise PromptError(f"missing variable: {var.name}")
        if len(values.get(var.name, "")) > var.max_chars:
            raise PromptError(f"{var.name} is longer than {var.max_chars} characters")
    safe = {k: _escape_closing_tags(v, declared) for k, v in values.items()}
    return PLACEHOLDER.sub(lambda m: safe.get(m[1], ""), prompt.body)


def _escape_closing_tags(value: str, declared: dict[str, Variable]) -> str:
    for name in declared:
        value = value.replace(f"</{name}>", f"&lt;/{name}&gt;")
    return value
