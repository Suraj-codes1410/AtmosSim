"""
Unit and verification tests for Overpass OpenStreetMap geographic source proxy ingestion.
"""

import json
import pytest

from atmosim.data.overpass import OverpassConnector, RawOsmFeature
from atmosim.physics.coordinates import LocalCoordinateSystem
from atmosim.sources.emissions import RoadNetworkSegmenter


@pytest.fixture
def sample_overpass_json():
    with open("tests/fixtures/sample_overpass_roads.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestOverpassParsingAndFeatures:
    """Test parsing of raw Overpass JSON payloads."""

    def test_parse_roads_and_industrial_features(self, sample_overpass_json):
        features = OverpassConnector.parse_response(sample_overpass_json)

        roads = [f for f in features if f.feature_category == "road"]
        industrials = [f for f in features if f.feature_category == "industrial"]

        assert len(roads) == 2
        assert len(industrials) == 2  # 1 industrial polygon way + 1 point source node

        # Verify primary road feature
        primary_road = next(r for r in roads if r.osm_id == 2001)
        assert primary_road.tags.get("highway") == "primary"
        assert len(primary_road.geometry) == 4

        # Verify point source chimney node
        chimney = next(ind for ind in industrials if ind.osm_id == 401)
        assert chimney.osm_type == "node"
        assert chimney.tags.get("man_made") == "chimney"

    def test_overpass_query_construction(self):
        query = OverpassConnector.build_query(
            min_lat=28.60, min_lon=77.20,
            max_lat=28.65, max_lon=77.25,
            include_roads=True,
            include_industrial=True,
        )

        assert "highway" in query
        assert "landuse" in query
        assert "28.60000,77.20000,28.65000,77.25000" in query


class TestRoadSegmentationAndLength:
    """Test metric Cartesian road segmentation and physical geodesic length calculation."""

    def test_road_length_metric_calculation(self, sample_overpass_json):
        features = OverpassConnector.parse_response(sample_overpass_json)
        primary_road = next(r for r in features if r.osm_id == 2001)

        coord = LocalCoordinateSystem(origin_lat=28.6139, origin_lon=77.2090)
        segments = RoadNetworkSegmenter.segment_osm_road(
            feature=primary_road,
            coord_system=coord,
            max_segment_len_m=250.0,
        )

        assert len(segments) > 0
        total_len = sum(s.length_meters for s in segments)

        # Geodesic distance for ~0.008 deg latitude + ~0.009 deg longitude span in Delhi is ~1.2 km (1200 m)
        assert 900.0 <= total_len <= 1500.0

        for seg in segments:
            assert 0.0 < seg.length_meters <= 250.0
            assert seg.road_class == "primary"
            assert seg.parent_osm_id == 2001
            assert len(seg.midpoint_cartesian) == 2
