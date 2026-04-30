"""Mai CLI - Permission module.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import getpass

from .global_config import get_global_roots
from .config import get_config, get_queue_sla

def get_all_roots(project_root: Path) -> List[str]:
    """Combine global roots and local roots."""
    roots = set(get_global_roots())
    
    # Also check local roots for backward compatibility
    cfg = get_config(project_root)
    local_roots = cfg.get("root", [])
    if isinstance(local_roots, str):
        roots.add(local_roots)
    else:
        roots.update(local_roots)
        
    # Fallback to OS user if no roots defined anywhere
    if not roots:
        try:
            roots.add(getpass.getuser())
        except Exception:
            roots.add("unknown")
            
    return list(roots)

def check_permission(
    project_root: Path,
    operator: str,
    action: str,
    issue: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Core Permission Matrix check.
    - root (global or local): ALL
    - owner (queue owner): create, complete, confirm, reject, reopen, escalate, discard
    - handler (current issue owner): claim, block, unblock, transfer, amend

    NOTE: For action="create", the `issue` dict MUST contain {"queue": "<queue_name>"}
          to determine the queue owner. If issue is None or lacks queue, returns False.
    """
    # 1. Global/Local Root check
    if operator in get_all_roots(project_root):
        return True

    # 2. Role Determination
    is_owner = False
    is_handler = False

    if issue:
        queue = issue.get("queue")
        queue_sla = get_queue_sla(project_root)
        q_owner, _ = queue_sla.get(queue, (None, None))
        
        # queue owner is considered owner
        if q_owner and operator == q_owner:
            is_owner = True

        # issue handler (the one who claimed it)
        if issue.get("owner") == operator:
            is_handler = True
            
        # backward compatibility for 'creator' (from v1.8)
        if not is_owner and issue.get("creator") == operator:
            is_owner = True

    # 3. Permission Matrix
    # Note: Actions like 'create' might not have an 'issue' yet, 
    # but they have a 'queue' context passed via the issue dict or similar.

    if action == "create":
        # For 'create', we check if operator is owner of the target queue
        if issue and issue.get("queue"):
            queue_sla = get_queue_sla(project_root)
            q_owner, _ = queue_sla.get(issue.get("queue"), (None, None))
            return operator == q_owner
        return False # Should not happen if caller provides queue info

    if action in ["complete", "confirm", "reject", "reopen", "escalate", "discard"]:
        return is_owner

    if action in ["claim"]:
        # Registered agents can claim
        cfg = get_config(project_root)
        is_registered_agent = operator in cfg.get("agents", {})
        return is_owner or is_registered_agent

    if action in ["block", "unblock", "transfer", "amend"]:
        return is_handler or is_owner

    return False

def check_project_permission(
    project_root: Path,
    operator: str,
    action: str
) -> bool:
    """
    Project-level permissions (no issue context).
    - init: root only
    - delete_project: root only
    """
    if action in ["init", "delete_project"]:
        # Only global or local roots can perform these high-privilege actions
        return operator in get_all_roots(project_root)
    
    return False
