import socket
import sys

from Compositions.demo import build_demo_backend


async def test_demo_changes_settings_without_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Demo must not connect to the network")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    backend = await build_demo_backend()
    await backend.init_all()
    await backend.set_water_heater_power(False)
    await backend.apply_water_heater_settings(57.0, "BOOST")
    assert backend._boiler.get_power() is False
    assert backend._boiler.get_target_temp() == 57.0
    assert backend._boiler.get_mode() == "BOOST"
    await backend.set_target_temp("Salon", 23.0)
    await backend.turn_on_heater("Julia")
    await backend.set_heater_target_temp("Julia", 22.5, 60)
    assert backend._climate.target_temp("Salon") == 23.0
    assert backend._heater.get_power("Julia") is True
    assert backend._heater.get_target_temp("Julia") == 22.5
    assert "Compositions.compositions" not in sys.modules
    fresh = await build_demo_backend()
    assert fresh._boiler.get_target_temp() == 55.0
