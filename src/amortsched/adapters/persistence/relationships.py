from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.sql.schema import Column, Table

from amortsched.core.entities import Entity
from amortsched.core.specifications import Rel

type PartitionedRelations = tuple[Sequence[Rel[Entity]], Sequence[Rel[Entity]]]


@dataclass(frozen=True, slots=True)
class Relationship:
    key: str
    table: Table
    entity: type
    root_key_column: Column[Any]
    related_key_column: Column[Any]
    many: bool = False


@dataclass(frozen=True, slots=True)
class PlannedRelation:
    relation: Rel[Entity]
    relationship: Relationship


@dataclass(frozen=True, slots=True)
class RelationshipPlan:
    joins: list[PlannedRelation]
    select_ins: list[PlannedRelation]


def plan_relations(config: dict[str, Relationship], relations: Sequence[Rel[Entity]]) -> RelationshipPlan:
    joins: list[PlannedRelation] = []
    select_ins: list[PlannedRelation] = []

    for relation in relations:
        relationship = config.get(relation.relation)
        if relationship is None:
            raise ValueError(f"Unknown relationship '{relation.relation}'")
        planned_relation = PlannedRelation(relation=relation, relationship=relationship)
        if relationship.many:
            select_ins.append(planned_relation)
        else:
            joins.append(planned_relation)

    return RelationshipPlan(joins=joins, select_ins=select_ins)


def partition_relations(config: dict[str, Relationship], relations: Sequence[Rel[Entity]]) -> PartitionedRelations:
    plan = plan_relations(config, relations)
    return [item.relation for item in plan.joins], [item.relation for item in plan.select_ins]
