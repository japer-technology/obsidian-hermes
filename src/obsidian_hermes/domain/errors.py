"""Closed error taxonomy for deterministic bridge failures."""


class HermesError(Exception):
    """Base class for expected Obsidian Hermes errors."""


class ConfigurationError(HermesError):
    """Deployment configuration is missing or unsafe."""


class ResourceError(HermesError):
    """A semantic resource cannot be accepted."""


class FrontmatterError(ResourceError):
    """A Markdown resource does not use the strict frontmatter profile."""


class SchemaError(ResourceError):
    """A resource schema is unknown or internally invalid."""


class ResourceValidationError(ResourceError):
    """A parsed resource does not conform to its exact v2 schema."""


class PathPolicyError(ResourceError):
    """A path violates a configured access-zone boundary."""


class StoreError(HermesError):
    """The operational store cannot safely perform an operation."""


class SafetyBlock(HermesError):
    """Execution is intentionally disabled until a safety precondition passes."""


class LifecycleError(HermesError):
    """A managed installation cannot be safely changed."""
