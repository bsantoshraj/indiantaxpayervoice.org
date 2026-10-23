"""Questionnaire definition shared by ingestion, aggregation and survey generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Question codes the aggregator depends on by name.
STATE = "STATE"
INDUSTRY = "INDUSTRY"
CONCERN = "CONCERN"

# Value used for an optional single-choice question left unanswered.
NOT_ANSWERED = "NA"
NOT_ANSWERED_LABEL = "Not answered"


@dataclass(frozen=True)
class Question:
    code: str
    role: str  # geography | breakdown | measure | distribution | private
    type: str  # list | multi | text
    required: bool
    text: str
    options: dict[str, str]
    max_answers: int | None = None

    def column(self, option: str) -> str:
        # LimeSurvey "code" headings name multiple-choice columns QCODE[SQCODE].
        return f"{self.code}[{option}]"

    def groups(self) -> dict[str, str]:
        """Options plus a "not answered" group for optional single-choice questions."""
        if self.required:
            return dict(self.options)
        return {**self.options, NOT_ANSWERED: NOT_ANSWERED_LABEL}


@dataclass(frozen=True)
class Schema:
    survey_version: str
    consent_code: str
    questions: dict[str, Question]

    def by_role(self, role: str) -> list[Question]:
        return [q for q in self.questions.values() if q.role == role]

    @property
    def singles(self) -> list[Question]:
        return [q for q in self.questions.values() if q.type == "list"]

    @property
    def multis(self) -> list[Question]:
        return [q for q in self.questions.values() if q.type == "multi"]

    @property
    def states(self) -> dict[str, str]:
        return self.questions[STATE].options

    @property
    def industries(self) -> dict[str, str]:
        return self.questions[INDUSTRY].options

    @property
    def concerns(self) -> dict[str, str]:
        return self.questions[CONCERN].options


def load_schema(path: str | Path) -> Schema:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    questions = {
        q["code"]: Question(
            code=q["code"],
            role=q["role"],
            type=q["type"],
            required=bool(q.get("required", False)),
            text=q["text"],
            options=dict(q.get("options", {})),
            max_answers=q.get("max_answers"),
        )
        for q in raw["questions"]
    }
    for code in (STATE, INDUSTRY, CONCERN):
        if code not in questions:
            raise ValueError(f"questionnaire must define {code}")
    return Schema(raw["survey_version"], raw["consent"]["code"], questions)
