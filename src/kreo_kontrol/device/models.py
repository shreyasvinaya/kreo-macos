"""Typed models for supported keyboards."""

from __future__ import annotations

from pydantic import BaseModel


class SupportedDevice(BaseModel):
    """A keyboard model the configurator knows how to talk to."""

    vendor_id: int
    product_id: int
    usage_page: int
    usage: int
    product_name: str
    protocol: str

