from turtlebot3_factory_nav.dispatcher_logic import (
    Action, Dispatcher, DOCK, NAVIGATE, REMOVE_BOX, SPAWN_BOX, State,
    STATION_DONE, STORAGE, WAIT)


def run_to_storage(d):
    """Drive a dispatcher serving one station up to the storage arrival."""
    d.on_nav_succeeded()
    d.on_dwell_done()


def test_starts_idle():
    d = Dispatcher()
    assert d.state == State.IDLE
    assert d.current is None
    assert d.queue == []


def test_request_when_idle_starts_trip():
    d = Dispatcher()
    assert d.on_request('A') == [Action(NAVIGATE, 'A')]
    assert d.state == State.TO_STATION
    assert d.current == 'A'


def test_full_cycle_one_station():
    d = Dispatcher(dwell_s=3.0)
    d.on_request('A')
    assert d.on_nav_succeeded() == [Action(WAIT, 3.0)]
    assert d.state == State.AT_STATION
    assert d.on_dwell_done() == [Action(REMOVE_BOX, 'A'), Action(NAVIGATE, STORAGE)]
    assert d.state == State.TO_STORAGE
    assert d.on_nav_succeeded() == [
        Action(SPAWN_BOX, 'A'), Action(STATION_DONE, 'A'), Action(NAVIGATE, DOCK)]
    assert d.state == State.TO_DOCK
    assert d.on_nav_succeeded() == []
    assert d.state == State.IDLE
    assert d.current is None


def test_fifo_order():
    d = Dispatcher()
    d.on_request('A')
    d.on_request('B')
    d.on_request('C')
    assert d.queue == ['B', 'C']
    run_to_storage(d)
    assert d.on_nav_succeeded()[-1] == Action(NAVIGATE, 'B')
    run_to_storage(d)
    assert d.on_nav_succeeded()[-1] == Action(NAVIGATE, 'C')


def test_duplicate_request_ignored():
    d = Dispatcher()
    d.on_request('A')
    assert d.on_request('A') == []
    d.on_request('B')
    assert d.on_request('B') == []
    assert d.queue == ['B']


def test_queue_cap():
    d = Dispatcher(max_queue=2)
    d.on_request('A')
    d.on_request('B')
    d.on_request('C')
    assert d.on_request('D') == []
    assert d.queue == ['B', 'C']


def test_request_while_docking_goes_to_station():
    d = Dispatcher()
    d.on_request('A')
    run_to_storage(d)
    d.on_nav_succeeded()
    assert d.state == State.TO_DOCK
    assert d.on_request('B') == [Action(NAVIGATE, 'B')]
    assert d.state == State.TO_STATION
    assert d.current == 'B'


def test_nav_fail_to_station_requeues_at_back():
    d = Dispatcher()
    d.on_request('A')
    d.on_request('B')
    assert d.on_nav_failed() == [Action(NAVIGATE, 'B')]
    assert d.current == 'B'
    assert d.queue == ['A']


def test_nav_fail_to_storage_retries_storage():
    d = Dispatcher()
    d.on_request('A')
    run_to_storage(d)
    assert d.on_nav_failed() == [Action(NAVIGATE, STORAGE)]
    assert d.state == State.TO_STORAGE
    assert d.current == 'A'


def test_events_in_wrong_state_are_ignored():
    d = Dispatcher()
    assert d.on_nav_succeeded() == []
    assert d.on_nav_failed() == []
    assert d.on_dwell_done() == []
    assert d.state == State.IDLE
    d.on_request('A')
    assert d.on_dwell_done() == []
    assert d.state == State.TO_STATION
