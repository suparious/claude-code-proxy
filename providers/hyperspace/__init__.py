"""SAP Hyperspace (HAI) provider - Anthropic-compatible native transport."""

from providers.defaults import HYPERSPACE_DEFAULT_BASE

from .client import HyperspaceProvider

__all__ = ["HYPERSPACE_DEFAULT_BASE", "HyperspaceProvider"]
