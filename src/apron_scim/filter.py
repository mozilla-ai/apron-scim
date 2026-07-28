"""SCIM filter parsing (RFC 7644 section 3.4.2.2).

Home for the filter tokenizer and parser producing a FilterNode AST, and the
FilterVisitor base class consumers subclass to translate filters to their own query
language. Implemented in Epic 2.
"""
