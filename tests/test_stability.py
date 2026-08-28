"""
Unit tests for atmospheric stability classification module (Pasquill-Gifford-Turner).
"""

import pytest
import math
from atmosim.physics.stability import (
    StabilityClass,
    InsolationCategory,
    determine_insolation_category,
    classify_stability,
)


class TestInsolationCategory:
    """Test solar insolation category determination."""

    def test_strong_insolation_radiation(self):
        assert determine_insolation_category(solar_radiation=750.0) == InsolationCategory.STRONG
        assert determine_insolation_category(solar_radiation=601.0) == InsolationCategory.STRONG

    def test_moderate_insolation_radiation(self):
        assert determine_insolation_category(solar_radiation=600.0) == InsolationCategory.MODERATE
        assert determine_insolation_category(solar_radiation=450.0) == InsolationCategory.MODERATE
        assert determine_insolation_category(solar_radiation=300.0) == InsolationCategory.MODERATE

    def test_slight_insolation_radiation(self):
        assert determine_insolation_category(solar_radiation=299.0) == InsolationCategory.SLIGHT
        assert determine_insolation_category(solar_radiation=100.0) == InsolationCategory.SLIGHT
        assert determine_insolation_category(solar_radiation=0.0) == InsolationCategory.SLIGHT

    def test_elevation_angles(self):
        assert determine_insolation_category(solar_elevation_deg=70.0) == InsolationCategory.STRONG
        assert determine_insolation_category(solar_elevation_deg=45.0) == InsolationCategory.MODERATE
        assert determine_insolation_category(solar_elevation_deg=20.0) == InsolationCategory.SLIGHT

    def test_invalid_insolation_inputs(self):
        with pytest.raises(ValueError, match="non-negative"):
            determine_insolation_category(solar_radiation=-10.0)

        with pytest.raises(ValueError, match="between 0 and 90"):
            determine_insolation_category(solar_elevation_deg=-5.0)

        with pytest.raises(ValueError, match="between 0 and 90"):
            determine_insolation_category(solar_elevation_deg=95.0)

        with pytest.raises(ValueError, match="Either 'solar_radiation'"):
            determine_insolation_category()


class TestClassifyStability:
    """Test comprehensive Pasquill stability classification table."""

    # 1. Daytime Strong Insolation (> 600 W/m²)
    @pytest.mark.parametrize(
        "wind_speed, expected",
        [
            (1.5, StabilityClass.A),
            (1.9, StabilityClass.A),
            (2.5, StabilityClass.A),
            (3.5, StabilityClass.B),
            (4.9, StabilityClass.B),
            (5.0, StabilityClass.C),
            (6.5, StabilityClass.C),
            (10.0, StabilityClass.C),
        ],
    )
    def test_daytime_strong_insolation(self, wind_speed, expected):
        res = classify_stability(wind_speed=wind_speed, solar_radiation=800.0)
        assert res == expected

    # 2. Daytime Moderate Insolation (300-600 W/m²)
    @pytest.mark.parametrize(
        "wind_speed, expected",
        [
            (1.5, StabilityClass.B),
            (2.5, StabilityClass.B),
            (3.5, StabilityClass.C),
            (4.5, StabilityClass.C),
            (5.5, StabilityClass.C),
            (6.0, StabilityClass.D),
            (8.0, StabilityClass.D),
        ],
    )
    def test_daytime_moderate_insolation(self, wind_speed, expected):
        res = classify_stability(wind_speed=wind_speed, solar_radiation=450.0)
        assert res == expected

    # 3. Daytime Slight Insolation (< 300 W/m²)
    @pytest.mark.parametrize(
        "wind_speed, expected",
        [
            (1.5, StabilityClass.B),
            (2.5, StabilityClass.C),
            (3.5, StabilityClass.C),
            (5.0, StabilityClass.D),
            (7.0, StabilityClass.D),
        ],
    )
    def test_daytime_slight_insolation(self, wind_speed, expected):
        res = classify_stability(wind_speed=wind_speed, solar_radiation=200.0)
        assert res == expected

    # 4. Nighttime Cloudy (>= 4/8 or >= 50% cloud cover)
    @pytest.mark.parametrize(
        "wind_speed, expected",
        [
            (1.5, StabilityClass.E),
            (2.5, StabilityClass.E),
            (3.5, StabilityClass.D),
            (5.0, StabilityClass.D),
            (7.0, StabilityClass.D),
        ],
    )
    def test_nighttime_cloudy(self, wind_speed, expected):
        res = classify_stability(wind_speed=wind_speed, is_daytime=False, cloud_cover=0.6)
        assert res == expected

    # 5. Nighttime Clear (< 4/8 or < 50% cloud cover)
    @pytest.mark.parametrize(
        "wind_speed, expected",
        [
            (1.5, StabilityClass.F),
            (2.5, StabilityClass.F),
            (3.5, StabilityClass.E),
            (5.0, StabilityClass.D),
            (7.0, StabilityClass.D),
        ],
    )
    def test_nighttime_clear(self, wind_speed, expected):
        res = classify_stability(wind_speed=wind_speed, is_daytime=False, cloud_cover=0.2)
        assert res == expected

    # 6. Overcast Invariant (>= 7/8 or >= 87.5% cloud cover is always D)
    @pytest.mark.parametrize(
        "wind_speed, is_daytime",
        [
            (1.5, True),
            (3.0, True),
            (1.5, False),
            (5.0, False),
        ],
    )
    def test_overcast_always_neutral(self, wind_speed, is_daytime):
        res = classify_stability(
            wind_speed=wind_speed,
            cloud_cover=0.9,
            is_daytime=is_daytime,
            solar_radiation=400.0 if is_daytime else 0.0,
        )
        assert res == StabilityClass.D

    def test_cloud_cover_units_handling(self):
        # 4 octas (0.5 fraction)
        res_octa = classify_stability(wind_speed=2.0, is_daytime=False, cloud_cover=4.0)
        assert res_octa == StabilityClass.E

        # 50 percent
        res_pct = classify_stability(wind_speed=2.0, is_daytime=False, cloud_cover=50.0)
        assert res_pct == StabilityClass.E

    def test_invalid_wind_speed(self):
        with pytest.raises(ValueError, match="strictly positive"):
            classify_stability(wind_speed=0.0, solar_radiation=500.0)

        with pytest.raises(ValueError, match="strictly positive"):
            classify_stability(wind_speed=-2.0, solar_radiation=500.0)

    def test_invalid_cloud_cover(self):
        with pytest.raises(ValueError, match="non-negative"):
            classify_stability(wind_speed=3.0, is_daytime=False, cloud_cover=-0.1)

        with pytest.raises(ValueError, match="out of valid range"):
            classify_stability(wind_speed=3.0, is_daytime=False, cloud_cover=120.0)

    def test_missing_nighttime_cloud_cover(self):
        with pytest.raises(ValueError, match="requires 'cloud_cover'"):
            classify_stability(wind_speed=3.0, is_daytime=False)

    def test_missing_daytime_information(self):
        with pytest.raises(ValueError, match="Unable to determine daytime"):
            classify_stability(wind_speed=3.0)

    def test_stability_class_enum_and_descriptions(self):
        for st in StabilityClass:
            assert isinstance(st.value, str)
            assert len(st.description) > 0
            assert str(st) == st.value
