import pytest

from apps.api.sse import encode_sse_event


def test_json_payload_cannot_inject_sse_fields() -> None:
    payload = {"message": 'ok\n\nevent: forged\ndata: {"admin":true}'}

    encoded = encode_sse_event(payload, event="message")

    assert encoded.startswith("event: message\ndata: {")
    assert "\ndata: {\"admin\":true}" not in encoded
    assert "\\nevent: forged" in encoded


@pytest.mark.parametrize("field", ["event", "event_id"])
def test_sse_metadata_rejects_line_breaks(field: str) -> None:
    kwargs = {field: "trusted\nforged"}

    with pytest.raises(ValueError, match="CR or LF"):
        encode_sse_event({"ok": True}, **kwargs)


def test_negative_retry_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        encode_sse_event({}, retry=-1)