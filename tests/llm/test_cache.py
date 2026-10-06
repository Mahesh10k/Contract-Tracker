"""Reply cache: same prompt, model and request give the same key; any change gives a new one."""

from pathlib import Path

from app.llm.cache import ReplyCache, cache_key

BODY = {"messages": [{"role": "user", "content": "1 Parties\nA and B."}]}


def test_the_same_inputs_give_the_same_key() -> None:
    assert cache_key("extract_fields@v1", "anthropic/claude-haiku-4.5", BODY) == cache_key(
        "extract_fields@v1", "anthropic/claude-haiku-4.5", BODY
    )


def test_tc0047_a_new_prompt_version_gives_a_new_key() -> None:
    v1 = cache_key("extract_fields@v1", "anthropic/claude-haiku-4.5", BODY)
    v2 = cache_key("extract_fields@v2", "anthropic/claude-haiku-4.5", BODY)

    assert v1 != v2


def test_tc0048_a_different_model_gives_a_new_key() -> None:
    a = cache_key("extract_fields@v1", "anthropic/claude-haiku-4.5", BODY)
    b = cache_key("extract_fields@v1", "google/gemini-3.1-flash-lite", BODY)

    assert a != b


def test_a_different_contract_text_gives_a_new_key() -> None:
    other = {"messages": [{"role": "user", "content": "1 Parties\nA and C."}]}

    assert cache_key("p@v1", "m", BODY) != cache_key("p@v1", "m", other)


def test_key_is_64_lowercase_hex_for_the_llm_calls_check() -> None:
    key = cache_key("p@v1", "m", BODY)

    assert len(key) == 64
    assert key == key.lower()
    assert all(ch in "0123456789abcdef" for ch in key)


def test_a_stored_reply_is_read_back_and_a_missing_one_is_none(tmp_path: Path) -> None:
    cache = ReplyCache(tmp_path)

    cache.put("a" * 64, {"content": "{}", "usage": {"prompt_tokens": 1}})

    assert cache.get("a" * 64) == {"content": "{}", "usage": {"prompt_tokens": 1}}
    assert cache.get("b" * 64) is None


def test_a_truncated_cache_file_is_a_miss_not_a_crash(tmp_path: Path) -> None:
    # TASK-002 review finding 6: a write killed half way left a file every run crashed on.
    (tmp_path / f"{'c' * 64}.json").write_text('{"content": "{\\"answ')

    assert ReplyCache(tmp_path).get("c" * 64) is None


def test_put_leaves_only_the_reply_file(tmp_path: Path) -> None:
    ReplyCache(tmp_path).put("d" * 64, {"content": "{}"})

    assert [p.name for p in tmp_path.iterdir()] == [f"{'d' * 64}.json"]
