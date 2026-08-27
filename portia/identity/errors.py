"""Typed failures for Portia identity and Actor Directory services."""

from __future__ import annotations


class PortiaIdentityError(RuntimeError):
    """Base class for production identity-service failures."""


class RosterResolutionError(PortiaIdentityError):
    """Base class for exact Core-roster resolution failures."""


class InvalidRosterIdentifierError(RosterResolutionError, ValueError):
    """A requested class or student identifier is invalid."""


class RosterNotFoundError(RosterResolutionError):
    """The explicitly requested class roster is absent."""


class RosterStudentNotFoundError(RosterResolutionError):
    """The requested student is absent from an existing authoritative roster."""


class RosterClassMismatchError(RosterResolutionError):
    """Core returned roster/student authority for another class."""


class RosterMalformedError(RosterResolutionError):
    """Core roster data is malformed, unsupported, or internally contradictory."""


class RosterAccessError(RosterResolutionError):
    """Core/workspace roster data could not be accessed reliably."""


class ActorDirectoryError(PortiaIdentityError):
    """Base class for Actor Directory application-service failures."""


class ActorDirectoryRemovedError(ActorDirectoryError):
    """The requested exact representation has an exceptional-removal certificate."""


class ActorNotCurrentError(ActorDirectoryError):
    """An Actor exists but is not eligible for current use."""


class ActorContactPointNotCurrentError(ActorDirectoryError):
    """A Contact Point exists but is not eligible for current use."""


class ActorRelationshipNotCurrentError(ActorDirectoryError):
    """An Actor-to-student Relationship exists but is not current-use eligible."""


class ActorRelationshipMalformedError(ActorDirectoryError):
    """A persisted Relationship cannot supply its required exact roster identity."""
