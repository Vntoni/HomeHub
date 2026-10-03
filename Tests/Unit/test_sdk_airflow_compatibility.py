"""Regression for the production SDK without eight-position support."""
import runpy
from pathlib import Path
from unittest.mock import Mock

import pyairstage.constants as constants
import pytest


@pytest.mark.parametrize("count", [4, 6])
def test_adapter_import_and_options_without_eight_position_enum(monkeypatch, count):
    monkeypatch.delattr(constants, "VerticalSwing8PositionsValues")
    namespace = runpy.run_path(str(Path(__file__).resolve().parents[2] /
                                  "Adapters/airstage_ac_adapter.py"))
    impl = Mock()
    impl.get_vertical_direction.return_value = constants.VerticalSwingPositions.HIGHEST
    impl.get_num_vertical_swing_positions.return_value = count
    impl.get_vertical_swing.return_value = constants.BooleanDescriptors.OFF
    adapter = namespace["AirstageACAdapter"]("test", Mock(), Mock(return_value=impl))
    assert len(adapter.get_airflow_options()) == count + 1
    assert adapter.get_airflow() == "HIGHEST"
