"""The scanner's output format. Plain Pydantic models, no dependency on the agent framework."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Category = Literal[
    "data-exfiltration",
    "credential-access",
    "hidden-instructions",
    "destructive-or-persistent-ops",
    "remote-code-fetch",
    "obfuscation",
]


class Evidence(BaseModel):
    """One piece of evidence: where it is and what it says."""

    file: str = Field(description="Path of the file, relative to the skill folder")
    line: int = Field(ge=1, description="Line number in that file, starting at 1")
    quote: str = Field(description="Short quote from that line")


class Verdict(BaseModel):
    """The model's judgment of one skill."""

    verdict: Literal["malicious", "benign"] = Field(description="Final classification of the skill")
    category: Category | None = Field(
        description="Primary attack category if malicious, otherwise null",
    )
    confidence: float = Field(ge=0, le=1, description="Confidence in the verdict, from 0 to 1")
    evidence: list[Evidence] = Field(description="Where in the skill the verdict comes from")
    reasoning: str = Field(description="One or two sentences explaining the verdict")

    @model_validator(mode="after")
    def benign_has_no_category(self) -> "Verdict":
        if self.verdict == "benign" and self.category is not None:
            raise ValueError("a benign verdict must not have a category")
        if self.verdict == "malicious" and self.category is None:
            raise ValueError("a malicious verdict must have a category")
        if self.verdict == "malicious" and not self.evidence:
            raise ValueError("a malicious verdict must have at least one piece of evidence")
        return self


class ScanResult(BaseModel):
    """What the scanner returns. The status is set by the scanner, never by the model."""

    status: Literal["scanned", "unscannable"]
    verdict: Verdict | None = None
    error: str | None = None
