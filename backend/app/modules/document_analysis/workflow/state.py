from typing import TypedDict


class AnalysisState(TypedDict, total=False):
    source: str
    require_review: bool
    candidate: dict
    approved: bool
