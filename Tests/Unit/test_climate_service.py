import asyncio

import pytest
from unittest.mock import MagicMock, AsyncMock
import pytest_asyncio

from pyairstage.constants import BooleanDescriptors

from App.climate_service import ClimateService
from Tests.Unit.test_data import *

class TestClimateService:

    # ============================================================
    # FIXTURES - Wspólny setup dla KAŻDEGO testu w klasie
    # ============================================================

    @pytest.fixture
    def service_all_rooms(self):
        """Serwis ze WSZYSTKIMI pokojami"""
        adapters = {}

        for room in ROOMS:
            adapter = AsyncMock()
            adapter.get_display_temperature = MagicMock(
                return_value=TEMPERATURES_INDOOR)
            adapter.set_target_temperature = AsyncMock()
            adapter.turn_on = AsyncMock()
            adapter.turn_off = AsyncMock()
            adapter.get_economy_mode = MagicMock()
            adapter.get_powerful_mode = MagicMock()
            adapter.get_outdoor_low_noise = MagicMock()
            adapter.get_target_temperature = MagicMock()
            adapters[room] = adapter

        return ClimateService(adapters), adapters
    # ============================================================
    # TESTY
    # ============================================================

# Inicjalizacja serwisu klimatyzacji i testy metod dostępowych

    def test_all_rooms_initialized(self, service_all_rooms):
        """Test: Czy wszystkie pokoje są zainicjalizowane?"""
        service, adapters = service_all_rooms
        assert len(adapters) == len(ROOMS)
        for room in ROOMS:
            assert room in adapters
        print(adapters)

# Testy getterów serwisu klimatyzacji dla różnych pokoi i stanów

    @pytest.mark.parametrize("indoor_rooms_temp", TEMPERATURES_INDOOR)
    @pytest.mark.parametrize("room", ROOMS)
    def test_get_indoor_temperature_salon(self, service_all_rooms, indoor_rooms_temp, room):
        """Test: Pobierz wewnętrzną temperaturę pokoi """
        service, adapters = service_all_rooms
        adapters[room].get_display_temperature.return_value = indoor_rooms_temp
        assert service.temp_indoor(room) == indoor_rooms_temp

    @pytest.mark.parametrize("booleans", BOOLEANS)
    @pytest.mark.parametrize("room", ROOMS)
    def test_get_economy_mode(self, service_all_rooms, booleans, room):
        """Test: Pobierz tryb ekonomiczny AC units"""
        service, adapters = service_all_rooms
        adapters[room].get_economy_mode.return_value = booleans
        assert service.economy(room) == booleans

    @pytest.mark.parametrize("booleans", BOOLEANS)
    @pytest.mark.parametrize("room", ROOMS)
    def test_get_powerful_mode(self, service_all_rooms, booleans, room):
        """Test: Pobierz tryb powerfull AC units"""
        service, adapters = service_all_rooms
        adapters[room].get_powerful_mode.return_value = booleans
        assert service.powerful(room) == booleans

    @pytest.mark.parametrize("booleans", BOOLEANS)
    @pytest.mark.parametrize("room", ROOMS)
    def test_get_low_noise(self, service_all_rooms, booleans, room):
        """Test: Pobierz tryb low noise AC units"""
        service, adapters = service_all_rooms
        adapters[room].get_outdoor_low_noise.return_value = booleans
        assert service.low_noise(room) == booleans

    @pytest.mark.parametrize("indoor_rooms_temp", TEMPERATURES_INDOOR)
    @pytest.mark.parametrize("room", ROOMS)
    def test_get_target_temp(self, service_all_rooms, indoor_rooms_temp, room):
        """Test: Pobierz docelową temperaturę AC units """
        service, adapters = service_all_rooms
        adapters[room].get_target_temperature.return_value = indoor_rooms_temp
        assert service.target_temp(room) == indoor_rooms_temp

# Testy setterów serwisu klimatyzacji dla różnych pokoi i stanów

    @pytest.mark.parametrize("indoor_rooms_temp", TEMPERATURES_INDOOR)
    @pytest.mark.parametrize("room", ROOMS)
    @pytest.mark.asyncio
    async def test_set_target_temp(self, service_all_rooms, indoor_rooms_temp, room):
        """Test: Ustaw docelową temperaturę AC units """
        service, adapters = service_all_rooms
        await service.set_target_temp(room, indoor_rooms_temp)
        adapters[room].set_target_temperature.assert_awaited_once_with(indoor_rooms_temp)

    @pytest.mark.parametrize("indoor_rooms_temp", TEMPERATURES_INDOOR)
    @pytest.mark.asyncio
    async def test_set_target_temp_negative(self, service_all_rooms, indoor_rooms_temp, room="Kuchnia"):
        """Test: Ustaw docelową temperaturę AC units z nieznanym pokojem"""
        service, adapters = service_all_rooms
        with pytest.raises(KeyError):
            await service.set_target_temp(room, indoor_rooms_temp)
            adapters[room].set_target_temperature.assert_awaited_once_with(indoor_rooms_temp)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("room", ROOMS)
    async def test_refresh_all(self, service_all_rooms, room):
        """Test: Odśwież wszystkie jednostki AC"""
        service, adapters = service_all_rooms
        await service.refresh_all()
        adapters[room].refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refresh_all_negative(self, service_all_rooms, room="Kuchnia"):
        """Test: Odśwież wszystkie jednostki AC z nieznanym pokojem"""
        service, adapters = service_all_rooms
        with pytest.raises(KeyError):
            await service.refresh_all()
            adapters[room].refresh.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("room", ROOMS)
    async def test_turn_on(self, service_all_rooms, room):
        """Test: Włącz jednostkę AC w danym pokoju"""
        service, adapters = service_all_rooms
        await service.turn_on(room)
        adapters[room].turn_on.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_turn_on_negative(self, service_all_rooms, room="Kuchnia"):
        """Test: Włącz jednostkę AC w nieznanym pokoju"""
        service, adapters = service_all_rooms
        with pytest.raises(KeyError):
            await service.turn_on(room)
            adapters[room].turn_on.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("room", ROOMS)
    async def test_turn_off(self, service_all_rooms, room):
        """Test: Wyłącz jednostkę AC w danym pokoju"""
        service, adapters = service_all_rooms
        await service.turn_off(room)
        adapters[room].turn_off.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_turn_off_negative(self, service_all_rooms, room="Kuchnia"):
        """Test: Wyłącz jednostkę AC w nieznanym pokoju"""
        service, adapters = service_all_rooms
        with pytest.raises(KeyError):
            await service.turn_off(room)
            adapters[room].turn_off.assert_awaited_once()

    @pytest.mark.parametrize("booleans", BOOLEANS)
    @pytest.mark.parametrize("room", ROOMS)
    @pytest.mark.asyncio
    async def test_set_economy_mode(self, service_all_rooms, booleans, room):
        """Test: Ustaw tryb ekonomiczny AC units"""
        service, adapters = service_all_rooms
        await service.set_economy(room, str(booleans))
        adapters[room].set_economy_mode.assert_awaited_once()

    @pytest.mark.parametrize("room", ROOMS)
    @pytest.mark.parametrize("mode", [1,2,"invalid", None, 3.5, "", -1])
    @pytest.mark.asyncio
    async def test_set_economy_mode_negative(self, service_all_rooms, room, mode):
        """Test: Ustaw tryb ekonomiczny AC units z nieznanym stanem"""
        service, adapters = service_all_rooms
        with pytest.raises(KeyError):
            await service.set_economy(room, mode)


    @pytest.mark.parametrize("booleans", BOOLEANS)
    @pytest.mark.parametrize("room", ROOMS)
    @pytest.mark.asyncio
    async def test_set_powerful_mode(self, service_all_rooms, booleans, room):
        """Test: Ustaw tryb powerful AC units"""
        service, adapters = service_all_rooms
        await service.set_powerful(room, str(booleans))
        adapters[room].set_powerful_mode.assert_awaited_once()

    @pytest.mark.parametrize("room", ROOMS)
    @pytest.mark.parametrize("mode", [1,2,"invalid", None, 3.5, "", -1])
    @pytest.mark.asyncio
    async def test_set_powerful_mode_negative(self, service_all_rooms, room, mode):
        """Test: Ustaw tryb powerful AC units z nieznanym stanem"""
        service, adapters = service_all_rooms
        with pytest.raises(KeyError):
            await service.set_powerful(room, mode)

    @pytest.mark.parametrize("booleans", BOOLEANS)
    @pytest.mark.parametrize("room", ROOMS)
    @pytest.mark.asyncio
    async def test_set_low_noise(self, service_all_rooms, booleans, room):
        """Test: Ustaw tryb low noise AC units"""
        service, adapters = service_all_rooms
        await service.set_low_noise(room, str(booleans))
        adapters[room].set_outdoor_low_noise.assert_awaited_once()

    @pytest.mark.parametrize("room", ROOMS)
    @pytest.mark.parametrize("mode", [1,2,"invalid", None, 3.5, "", -1])
    @pytest.mark.asyncio
    async def test_set_low_noise_negative(self, service_all_rooms, room, mode):
        """Test: Ustaw tryb low noise AC units z nieznanym stanem"""
        service, adapters = service_all_rooms
        with pytest.raises(KeyError):
            await service.set_low_noise(room, mode)


