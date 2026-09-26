"""
Unit tests for spatial relationship graph.

Tests spatial relationship types, graph operations, and architectural queries.
"""

import pytest

from knowledge.spatial.relationships import (
    SpatialRelationType,
    SpatialRelationship,
    SpatialRelationshipGraph,
)


class TestSpatialRelationship:
    """Test SpatialRelationship dataclass."""

    def test_create_relationship(self):
        """Test creating a spatial relationship."""
        rel = SpatialRelationship(
            source_id="room_1",
            target_id="room_2",
            relation_type=SpatialRelationType.ADJACENT,
            metadata={"shared_wall": "wall_5"},
        )

        assert rel.source_id == "room_1"
        assert rel.target_id == "room_2"
        assert rel.relation_type == SpatialRelationType.ADJACENT
        assert rel.metadata["shared_wall"] == "wall_5"

    def test_create_from_string_type(self):
        """Test creating relationship with string type (auto-converts to enum)."""
        rel = SpatialRelationship(
            source_id="room_1",
            target_id="room_2",
            relation_type="adjacent",
        )

        assert rel.relation_type == SpatialRelationType.ADJACENT

    def test_to_dict(self):
        """Test serialization to dictionary."""
        rel = SpatialRelationship(
            source_id="room_1",
            target_id="room_2",
            relation_type=SpatialRelationType.CONNECTS_TO,
            metadata={"door_id": "door_3"},
        )

        data = rel.to_dict()

        assert data["source_id"] == "room_1"
        assert data["target_id"] == "room_2"
        assert data["relation_type"] == "connects_to"
        assert data["metadata"]["door_id"] == "door_3"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "source_id": "room_1",
            "target_id": "room_2",
            "relation_type": "adjacent",
            "metadata": {"shared_wall": "wall_5"},
        }

        rel = SpatialRelationship.from_dict(data)

        assert rel.source_id == "room_1"
        assert rel.target_id == "room_2"
        assert rel.relation_type == SpatialRelationType.ADJACENT
        assert rel.metadata["shared_wall"] == "wall_5"


class TestSpatialRelationshipGraph:
    """Test SpatialRelationshipGraph operations."""

    @pytest.fixture
    def graph(self):
        """Create a sample architectural graph."""
        g = SpatialRelationshipGraph()

        # Room layout: entrance, living room, bedroom, kitchen
        g.add_relationship("entrance", "living_room", SpatialRelationType.CONNECTS_TO, {"door_id": "door_1"})
        g.add_relationship("entrance", "living_room", SpatialRelationType.ADJACENT)
        g.add_relationship("living_room", "bedroom", SpatialRelationType.ADJACENT)
        g.add_relationship("living_room", "bedroom", SpatialRelationType.CONNECTS_TO, {"door_id": "door_2"})
        g.add_relationship("living_room", "kitchen", SpatialRelationType.ADJACENT)
        g.add_relationship("living_room", "kitchen", SpatialRelationType.CONNECTS_TO, {"door_id": "door_3"})

        # Containment
        g.add_relationship("building", "entrance", SpatialRelationType.CONTAINS)
        g.add_relationship("building", "living_room", SpatialRelationType.CONTAINS)
        g.add_relationship("building", "bedroom", SpatialRelationType.CONTAINS)
        g.add_relationship("building", "kitchen", SpatialRelationType.CONTAINS)

        # Separation
        g.add_relationship("wall_1", "entrance", SpatialRelationType.SEPARATES)
        g.add_relationship("wall_1", "living_room", SpatialRelationType.SEPARATES)
        g.add_relationship("wall_2", "living_room", SpatialRelationType.SEPARATES)
        g.add_relationship("wall_2", "bedroom", SpatialRelationType.SEPARATES)

        # Vertical relationships
        g.add_relationship("column_1", "beam_1", SpatialRelationType.SUPPORTS)
        g.add_relationship("beam_1", "roof_slab", SpatialRelationType.SUPPORTS)
        g.add_relationship("floor_2", "floor_1", SpatialRelationType.ABOVE)

        # Orientation
        g.add_relationship("window_1", "street", SpatialRelationType.FACES)
        g.add_relationship("kitchen", "service_area", SpatialRelationType.BACKS_ONTO)

        return g

    def test_add_relationship(self):
        """Test adding relationships to graph."""
        g = SpatialRelationshipGraph()
        rel = g.add_relationship("room_1", "room_2", SpatialRelationType.ADJACENT)

        assert len(g.relationships) == 1
        assert rel.source_id == "room_1"
        assert rel.target_id == "room_2"
        assert rel.relation_type == SpatialRelationType.ADJACENT

    def test_add_relationship_with_string_type(self):
        """Test adding relationship using string type."""
        g = SpatialRelationshipGraph()
        rel = g.add_relationship("room_1", "room_2", "adjacent")

        assert rel.relation_type == SpatialRelationType.ADJACENT

    def test_get_relationships_from(self, graph):
        """Test querying relationships from a component."""
        rels = graph.get_relationships_from("living_room")

        assert len(rels) == 4  # 2 adjacent + 2 connects_to (bedroom, kitchen)
        targets = [r.target_id for r in rels]
        assert "bedroom" in targets
        assert "kitchen" in targets

    def test_get_relationships_from_with_type_filter(self, graph):
        """Test querying relationships from a component filtered by type."""
        rels = graph.get_relationships_from("living_room", SpatialRelationType.CONNECTS_TO)

        assert len(rels) == 2  # bedroom and kitchen connections
        targets = [r.target_id for r in rels]
        assert "bedroom" in targets
        assert "kitchen" in targets

    def test_get_relationships_to(self, graph):
        """Test querying relationships targeting a component."""
        rels = graph.get_relationships_to("living_room")

        assert len(rels) >= 2  # From entrance and building container

    def test_get_relationships_by_type(self, graph):
        """Test querying all relationships of a specific type."""
        rels = graph.get_relationships_by_type(SpatialRelationType.SUPPORTS)

        assert len(rels) == 2
        support_pairs = [(r.source_id, r.target_id) for r in rels]
        assert ("column_1", "beam_1") in support_pairs
        assert ("beam_1", "roof_slab") in support_pairs

    def test_get_adjacent_components(self, graph):
        """Test getting adjacent components."""
        adjacent = graph.get_adjacent_components("living_room")

        assert len(adjacent) == 2
        assert "bedroom" in adjacent
        assert "kitchen" in adjacent

    def test_get_connected_components(self, graph):
        """Test getting connected components (via doors)."""
        connected = graph.get_connected_components("living_room")

        assert len(connected) == 2
        assert "bedroom" in connected
        assert "kitchen" in connected

    def test_get_contained_components(self, graph):
        """Test getting components contained within another."""
        contained = graph.get_contained_components("building")

        assert len(contained) == 4
        assert "entrance" in contained
        assert "living_room" in contained
        assert "bedroom" in contained
        assert "kitchen" in contained

    def test_get_container(self, graph):
        """Test getting the container of a component."""
        container = graph.get_container("entrance")

        assert container == "building"

    def test_get_container_none(self, graph):
        """Test getting container when component has no container."""
        container = graph.get_container("building")

        assert container is None

    def test_get_supported_components(self, graph):
        """Test getting components supported by a structural element."""
        supported = graph.get_supported_components("column_1")

        assert len(supported) == 1
        assert "beam_1" in supported

    def test_get_supporting_components(self, graph):
        """Test getting components that support a given component."""
        supports = graph.get_supporting_components("roof_slab")

        assert len(supports) == 1
        assert "beam_1" in supports

    def test_what_does_separate(self, graph):
        """Test querying what spaces a separator divides."""
        side_a, side_b = graph.what_does_separate("wall_1")

        assert "entrance" in side_a or "entrance" in side_b
        assert "living_room" in side_a or "living_room" in side_b

    def test_what_does_separate_empty(self, graph):
        """Test querying separator with insufficient relationships."""
        side_a, side_b = graph.what_does_separate("nonexistent_wall")

        assert side_a == []
        assert side_b == []

    def test_get_facing_components(self, graph):
        """Test getting components that another component faces."""
        facing = graph.get_facing_components("window_1")

        assert len(facing) == 1
        assert "street" in facing

    def test_clear(self, graph):
        """Test clearing all relationships."""
        assert len(graph.relationships) > 0

        graph.clear()

        assert len(graph.relationships) == 0
        assert len(graph._by_source) == 0
        assert len(graph._by_target) == 0
        assert len(graph._by_type) == 0

    def test_to_dict(self, graph):
        """Test serializing graph to dictionary."""
        data = graph.to_dict()

        assert "relationships" in data
        assert len(data["relationships"]) > 0
        assert data["relationships"][0]["source_id"] is not None
        assert data["relationships"][0]["relation_type"] is not None

    def test_from_dict(self, graph):
        """Test deserializing graph from dictionary."""
        data = graph.to_dict()
        new_graph = SpatialRelationshipGraph.from_dict(data)

        assert len(new_graph.relationships) == len(graph.relationships)

        # Verify a sample relationship
        original_adjacent = graph.get_adjacent_components("living_room")
        restored_adjacent = new_graph.get_adjacent_components("living_room")
        assert set(original_adjacent) == set(restored_adjacent)


class TestSpatialRelationType:
    """Test SpatialRelationType enum."""

    def test_all_relation_types_exist(self):
        """Test that all expected relation types are defined."""
        expected_types = [
            "ADJACENT",
            "CONTAINS",
            "CONNECTS_TO",
            "SEPARATES",
            "ABOVE",
            "BELOW",
            "SUPPORTS",
            "FACES",
            "BACKS_ONTO",
            "NEAR",
            "ALIGNED_WITH",
        ]

        for type_name in expected_types:
            assert hasattr(SpatialRelationType, type_name)

    def test_enum_values_are_lowercase(self):
        """Test that enum values follow lowercase convention."""
        for rel_type in SpatialRelationType:
            assert rel_type.value.islower()
            assert "_" in rel_type.value or rel_type.value.isalpha()
