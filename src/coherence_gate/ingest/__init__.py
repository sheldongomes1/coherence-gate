"""Ingestion: PDF -> canonical parsed markdown (v0.2 CS2). One interface, swappable vendors.
No module outside this package imports the vendor SDK."""
from .parser import LocalParser, MixedbreadParser, ParseResult, Parser, get_parser, parse_document

__all__ = ["Parser", "ParseResult", "MixedbreadParser", "LocalParser", "get_parser", "parse_document"]
