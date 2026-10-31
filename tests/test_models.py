import pytest

from wizardindex.models import canonical, effort


@pytest.mark.parametrize("raw, expected", [
    # The spellings models.py's docstring promises to collapse into one id.
    ("Opus 5 [high]", "opus-5"),
    ("claude-opus-5", "opus-5"),
    ("anthropic/claude-opus-5", "opus-5"),
    ("Claude Opus 5 (Max)", "opus-5"),
    ("Claude 4.1 Opus", "opus-4-1"),
    # Efforts, thinking budgets and dated API snapshots are settings, not models.
    ("claude-opus-5-5-xhigh", "opus-5-5"),
    ("GPT-6.1 Sol (Xhigh)", "gpt-6-1-sol"),
    ("claude-sonnet-4-20250514", "sonnet-4"),
    ("claude-3-7-sonnet-thinking-32k", "sonnet-3-7"),
    ("Gemini 4 Argon - Vertex", "gemini-4-argon"),
    ("deepseek-ai/DeepSeek-V3p2", "deepseek-v3-2"),
    # MMDD suffixes mark distinct re-released models and are kept.
    ("deepseek-v4-1-flash-1017", "deepseek-v4-1-flash-1017"),
    # data/aliases.yaml fixes what the rules get wrong.
    ("Claude 4.7", "opus-4-7"),
    ("Qwen3.8 Max", "qwen3-8-max"),
])
def test_canonical(raw, expected):
    assert canonical(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("Opus 5 [high]", "high"),
    ("Claude Opus 5 (Max)", "max"),
    ("claude-opus-5-5-xhigh", "xhigh"),
    ("GPT-6.1 Sol (Xhigh)", "xhigh"),
    ("claude-opus-5-5", None),
    ("Claude Opus 5 (Preview)", None),   # bracketed, but not an effort
])
def test_effort(raw, expected):
    assert effort(raw) == expected
