"""Explicit named-route queries into current Agent-system knowledge.

Historical public names are retained for compatibility.
"""

from .action_trigger import KnowledgeActionTrigger, TriggerError

__all__ = ["KnowledgeActionTrigger", "TriggerError"]
