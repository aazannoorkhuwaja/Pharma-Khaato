"""High-DPI desktop sizing: protect reachable checkout on 1366x768 laptops."""
import pytest

from ui.theme.layout import LayoutMetrics


@pytest.mark.parametrize("logical_available", [
    (910, 480),      # common 1366x768 / 150% minus taskbar
    (1093, 585),     # common 1366x768 / 125% minus taskbar
    (1366, 730),
    (1920, 1040),
])
def test_startup_window_never_exceeds_available_logical_desktop(logical_available):
    available_w, available_h = logical_available
    width, height = LayoutMetrics.startup_window_size(available_w, available_h)
    assert LayoutMetrics.SHELL_MIN_WIDTH <= width <= available_w
    assert LayoutMetrics.SHELL_MIN_HEIGHT <= height <= available_h
    assert width <= 1440 and height <= 900


def test_physical_laptop_scaled_150_fits_within_usable_desktop():
    # App receives logical geometry from Qt; applying another /1.5 is incorrect.
    assert LayoutMetrics.startup_window_size(910, 480) == (855, 440)


def test_shell_height_safely_below_150_percent_laptop_workspace():
    assert LayoutMetrics.SHELL_MIN_HEIGHT <= 440
    assert LayoutMetrics.SHELL_MIN_WIDTH <= 855


def test_monitor_geometry_is_not_double_scaled():
    # 940x520 is *already* DPI-adjusted, not raw physical monitor pixels.
    w, h = LayoutMetrics.startup_window_size(940, 520)
    assert w >= 850 and h >= 440
