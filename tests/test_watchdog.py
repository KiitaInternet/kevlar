from kevlar_agent import Watchdog
from kevlar_agent.watchdog import Watched


def test_alive_process_is_not_restarted():
    started = []

    watched = Watched(
        name="fake_service",
        start=["python", "-c", "pass"],
        is_alive=lambda: True,
    )
    wd = Watchdog([watched])
    restarted = wd.check_and_restart()
    assert restarted == []


def test_dead_process_is_restarted(monkeypatch):
    started = []

    def fake_popen(argv):
        started.append(argv)

        class FakeProc:
            pass

        return FakeProc()

    monkeypatch.setattr("kevlar_agent.watchdog.subprocess.Popen", fake_popen)

    watched = Watched(
        name="fake_service",
        start=["python", "fake_service.py"],
        is_alive=lambda: False,
    )
    wd = Watchdog([watched])
    restarted = wd.check_and_restart()

    assert restarted == ["fake_service"]
    assert started == [["python", "fake_service.py"]]


def test_multiple_watched_only_dead_ones_restart(monkeypatch):
    started = []
    monkeypatch.setattr(
        "kevlar_agent.watchdog.subprocess.Popen",
        lambda argv: started.append(argv),
    )

    alive = Watched(name="alive_one", start=["x"], is_alive=lambda: True)
    dead = Watched(name="dead_one", start=["y"], is_alive=lambda: False)

    wd = Watchdog([alive, dead])
    restarted = wd.check_and_restart()

    assert restarted == ["dead_one"]
    assert started == [["y"]]


def test_restart_failure_is_reported_not_raised(monkeypatch):
    def boom(argv):
        raise OSError("no such file")

    monkeypatch.setattr("kevlar_agent.watchdog.subprocess.Popen", boom)

    watched = Watched(name="broken", start=["z"], is_alive=lambda: False)
    wd = Watchdog([watched])
    restarted = wd.check_and_restart()  # must not raise

    assert len(restarted) == 1
    assert "broken" in restarted[0]
