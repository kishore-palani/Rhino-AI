"""
Spatial relationship definitions and graph for architectural reasoning.

Defines how building components relate spatially and provides a query
interface for architectural constraints based on these relationships.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class SpatialRelationType(str, Enum):
    """Types of spatial relationships between building components."""

    # Topological relationships
    ADJACENT = "adjacent"  # Shares boundary (walls, rooms)
    CONTAINS = "contains"  # One component encloses another
    CONNECTS_TO = "connects_to"  # Linked by door, corridor, stair
    SEPARATES = "separates"  # Divides two spaces (wall, partition)

    # Vertical relationships
    ABOVE = "above"  # Vertically positioned over another
    BELOW = "below"  # Vertically positioned under another
    SUPPORTS = "supports"  # Structural support relationship

    # Orientation relationships
    FACES = "faces"  # Oriented toward (window faces street)
    BACKS_ONTO = "backs_onto"  # Rear orientation (kitchen backs onto service)

    # Proximity relationships
    NEAR = "near"  # Close proximity without direct contact
    ALIGNED_WITH = "aligned_with"  # Geometrically aligned (axes, grids)


@dataclass
class SpatialRelationship:
    """A spatial relationship between two building components."""

    source_id: str  # Component ID (e.g., "room_1", "wall_3")
    target_id: str  # Related component ID
    relation_type: SpatialRelationType
    metadata: dict[str, Any] = field(default_factory=dict)  # Distance, shared edge, etc.

    def __post_init__(self):
        """Validate and convert relation_type to enum if needed."""
        if isinstance(self.relation_type, str):
            self.relation_type = SpatialRelationType(self.relation_type)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpatialRelationship":
        """Create from dictionary."""
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=SpatialRelationType(data["relation_type"]),
            metadata=data.get("metadata", {}),
        )


class SpatialRelationshipGraph:
    """
    Graph of spatial relationships between building components.

    Enables architectural reasoning queries like:
    - Which rooms are adjacent to the entrance?
    - What does this wall separate?
    - Which rooms have windows facing the street?
    - What components are supported by this column?
    """

    def __init__(self):
        self.relationships: list[SpatialRelationship] = []
        # Index: source_id -> list of relationships
        self._by_source: dict[str, list[SpatialRelationship]] = {}
        # Index: target_id -> list of relationships
        self._by_target: dict[str, list[SpatialRelationship]] = {}
        # Index: relation_type -> list of relationships
        self._by_type: dict[SpatialRelationType, list[SpatialRelationship]] = {}

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: SpatialRelationType | str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SpatialRelationship:
        """Add a spatial relationship to the graph."""
        if isinstance(relation_type, str):
            relation_type = SpatialRelationType(relation_type)

        rel = SpatialRelationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            metadata=metadata or {},
        )

        self.relationships.append(rel)

        # Update indexes
        self._by_source.setdefault(source_id, []).append(rel)
        self._by_target.setdefault(target_id, []).append(rel)
        self._by_type.setdefault(relation_type, []).append(rel)

        return rel

    def get_relationships_from(
        self,
        source_id: str,
        relation_type: Optional[SpatialRelationType | str] = None,
    ) -> list[SpatialRelationship]:
        """Get all relationships originating from a component."""
        rels = self._by_source.get(source_id, [])

        if relation_type:
            if isinstance(relation_type, str):
                relation_type = SpatialRelationType(relation_type)
            rels = [r for r in rels if r.relation_type == relation_type]

        return rels

    def get_relationships_to(
        self,
        target_id: str,
        relation_type: Optional[SpatialRelationType | str] = None,
    ) -> list[SpatialRelationship]:
        """Get all relationships targeting a component."""
        rels = self._by_target.get(target_id, [])

        if relation_type:
            if isinstance(relation_type, str):
                relation_type = SpatialRelationType(relation_type)
            rels = [r for r in rels if r.relation_type == relation_type]

        return rels

    def get_relationships_by_type(
        self, relation_type: SpatialRelationType | str
    ) -> list[SpatialRelationship]:
        """Get all relationships of a specific type."""
        if isinstance(relation_type, str):
            relation_type = SpatialRelationType(relation_type)
        return self._by_type.get(relation_type, [])

    def get_adjacent_components(self, component_id: str) -> list[str]:
        """Get all components adjacent to the given component."""
        rels = self.get_relationships_from(component_id, SpatialRelationType.ADJACENT)
        return [r.target_id for r in rels]

    def get_connected_components(self, component_id: str) -> list[str]:
        """Get all components connected to the given component (e.g., by door)."""
        rels = self.get_relationships_from(component_id, SpatialRelationType.CONNECTS_TO)
        return [r.target_id for r in rels]

    def get_contained_components(self, container_id: str) -> list[str]:
        """Get all components contained within the given component."""
        rels = self.get_relationships_from(container_id, SpatialRelationType.CONTAINS)
        return [r.target_id for r in rels]

    def get_container(self, component_id: str) -> Optional[str]:
        """Get the component that contains the given component."""
        rels = self.get_relationships_to(component_id, SpatialRelationType.CONTAINS)
        return rels[0].source_id if rels else None

    def get_supported_components(self, support_id: str) -> list[str]:
        """Get all components supported by the given structural element."""
        rels = self.get_relationships_from(support_id, SpatialRelationType.SUPPORTS)
        return [r.target_id for r in rels]

    def get_supporting_components(self, component_id: str) -> list[str]:
        """Get all components that support the given component."""
        rels = self.get_relationships_to(component_id, SpatialRelationType.SUPPORTS)
        return [r.source_id for r in rels]

    def what_does_separate(self, separator_id: str) -> tuple[list[str], list[str]]:
        """
        Get what spaces/components a separator (wall, partition) divides.

        Returns:
            Tuple of (spaces_on_one_side, spaces_on_other_side)
        """
        rels = self.get_relationships_from(separator_id, SpatialRelationType.SEPARATES)

        if len(rels) < 2:
            return ([], [])

        # Separators typically have two targets (the two spaces they divide)
        side_a = [rels[0].target_id] if rels else []
        side_b = [r.target_id for r in rels[1:]]

        return (side_a, side_b)

    def get_facing_components(self, component_id: str) -> list[str]:
        """Get components that this component faces (e.g., window faces street)."""
        rels = self.get_relationships_from(component_id, SpatialRelationType.FACES)
        return [r.target_id for r in rels]

    def clear(self):
        """Clear all relationships from the graph."""
        self.relationships.clear()
        self._by_source.clear()
        self._by_target.clear()
        self._by_type.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "relationships": [r.to_dict() for r in self.relationships],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpatialRelationshipGraph":
        """Deserialize graph from dictionary."""
        graph = cls()
        for rel_data in data.get("relationships", []):
            rel = SpatialRelationship.from_dict(rel_data)
            graph.add_relationship(
                rel.source_id,
                rel.target_id,
                rel.relation_type,
                rel.metadata,
            )
        return graph
