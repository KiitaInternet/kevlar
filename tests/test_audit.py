from kevlar_agent import AuditLog


def test_record_and_tail_round_trip(tmp_path):
    log = AuditLog(tmp_path)
    log.record("send_email", {"to": "x@example.com"}, result="sent", source="voice")
    log.record("check_calendar", {}, result="3 events", source="telegram")

    rows = log.tail(limit=10)
    assert len(rows) == 2
    assert rows[0]["tool"] == "check_calendar"  # newest first
    assert rows[1]["tool"] == "send_email"


def test_tail_can_filter_by_tool(tmp_path):
    log = AuditLog(tmp_path)
    log.record("tool_a", result="ok")
    log.record("tool_b", result="ok")
    log.record("tool_a", result="ok again")

    rows = log.tail(tool="tool_a")
    assert len(rows) == 2
    assert all(r["tool"] == "tool_a" for r in rows)


def test_record_never_raises_on_bad_input(tmp_path):
    log = AuditLog(tmp_path)

    class Unserializable:
        def __repr__(self):
            raise RuntimeError("boom")

    log.record("weird_tool", Unserializable())  # must not raise
    rows = log.tail()
    assert rows[0]["tool"] == "weird_tool"


def test_empty_log_directory_returns_empty_list(tmp_path):
    log = AuditLog(tmp_path / "does_not_exist_yet")
    assert log.tail() == []
