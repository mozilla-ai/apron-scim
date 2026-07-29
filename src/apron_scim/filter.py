"""SCIM filter parsing (RFC 7644 section 3.4.2.2).

Home for the filter grammar's AST (:data:`FilterNode` and its node types), the
:func:`parse_filter` entry point, and the :class:`FilterVisitor` base class consumers
subclass to translate a parsed filter into their own query language (onoma emits
SQLModel). The tokenizer/parser bodies land in Epic 2; this module ratifies the node
schema and visitor contract those bodies conform to.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeAlias, TypeVar, assert_never

T = TypeVar("T")


class CompareOp(StrEnum):
    """The binary comparison operators of the SCIM filter grammar (RFC 7644 section 3.4.2.2).

    Presence (``pr``) is not a binary comparison and is represented by :class:`Present`
    rather than a member here.
    """

    EQ = "eq"
    NE = "ne"
    CO = "co"
    SW = "sw"
    EW = "ew"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"


@dataclass(frozen=True, slots=True)
class Comparison:
    """A binary comparison of an attribute against a literal value.

    Attributes:
        attribute_path: The dotted attribute path being compared, e.g.
            ``userName`` or ``name.familyName``.
        op: The comparison operator.
        value: The literal right-hand operand, carried as parsed JSON data (never
            interpolated into a query string), or ``None`` for a ``null`` literal.
    """

    attribute_path: str
    op: CompareOp
    value: str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class Present:
    """A presence test (``attribute_path pr``): the attribute has a non-empty value."""

    attribute_path: str


@dataclass(frozen=True, slots=True)
class And:
    """Logical conjunction of two sub-filters."""

    left: FilterNode
    right: FilterNode


@dataclass(frozen=True, slots=True)
class Or:
    """Logical disjunction of two sub-filters."""

    left: FilterNode
    right: FilterNode


@dataclass(frozen=True, slots=True)
class Not:
    """Logical negation of a sub-filter."""

    operand: FilterNode


@dataclass(frozen=True, slots=True)
class ValuePath:
    """A predicate applied to elements of a multi-valued attribute.

    Models the ``attribute_path[predicate]`` form, e.g. ``emails[type eq "work"]``.

    Attributes:
        attribute_path: The multi-valued attribute the predicate selects within.
        predicate: The filter evaluated against each element's sub-attributes.
    """

    attribute_path: str
    predicate: FilterNode


FilterNode: TypeAlias = Comparison | Present | And | Or | Not | ValuePath
"""A node of the parsed SCIM filter AST."""


class FilterVisitor(ABC, Generic[T]):
    """Base class translating a parsed filter into a target representation of type ``T``.

    Consumers subclass this and implement one ``visit_*`` method per node type to
    emit their query language; :meth:`visit` dispatches a node to the matching method.
    Recursion is the subclass's responsibility: a ``visit_and`` implementation
    typically calls ``self.visit(node.left)`` and ``self.visit(node.right)`` and
    combines the results. Values reach the subclass as data on the nodes, so a
    filter cannot be coerced into query injection.
    """

    def visit(self, node: FilterNode) -> T:
        """Dispatch ``node`` to the ``visit_*`` method for its type.

        Args:
            node: The AST node to translate.

        Returns:
            The subclass's translation of ``node``.
        """
        match node:
            case Comparison():
                return self.visit_comparison(node)
            case Present():
                return self.visit_present(node)
            case And():
                return self.visit_and(node)
            case Or():
                return self.visit_or(node)
            case Not():
                return self.visit_not(node)
            case ValuePath():
                return self.visit_value_path(node)
            case _:
                assert_never(node)

    @abstractmethod
    def visit_comparison(self, node: Comparison) -> T:
        """Translate a binary comparison."""

    @abstractmethod
    def visit_present(self, node: Present) -> T:
        """Translate a presence test."""

    @abstractmethod
    def visit_and(self, node: And) -> T:
        """Translate a logical conjunction."""

    @abstractmethod
    def visit_or(self, node: Or) -> T:
        """Translate a logical disjunction."""

    @abstractmethod
    def visit_not(self, node: Not) -> T:
        """Translate a logical negation."""

    @abstractmethod
    def visit_value_path(self, node: ValuePath) -> T:
        """Translate a multi-valued attribute predicate."""


def parse_filter(expr: str) -> FilterNode:
    """Parse a SCIM filter expression (RFC 7644 section 3.4.2.2) into a :data:`FilterNode`.

    Args:
        expr: The raw filter expression, e.g. ``userName eq "bjensen"``.

    Returns:
        The root of the parsed filter AST.

    Raises:
        InvalidFilter: If ``expr`` is not a well-formed SCIM filter.
    """
    raise NotImplementedError
