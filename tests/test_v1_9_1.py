import tempfile
import pytest
from pathlib import Path
from mai.config import save_config, clear_config_cache
from mai.issue import cmd_issue_new, cmd_issue_claim, check_permission, read_issue
from mai.issue_list import cmd_issue_show

def setup_project(root: Path):
    clear_config_cache()
    mai_dir = root / ".mai"
    if not mai_dir.exists():
        mai_dir.mkdir()
    config = {
        "queues": {
            "questions": {"owner": "alice", "sla_minutes": 60}
        },
        "agents": {
            "alice": {"heartbeat_minutes": 30},
            "bob": {"heartbeat_minutes": 30}
        }
    }
    save_config(root, config)

def test_v1_9_1_handler_permissions():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        setup_project(root)
        
        cmd_issue_new(root, "questions", "Test Permissions", ref=None, operator="alice")
        issue_id = list((root / ".mai" / "queues" / "questions").glob("*.md"))[0].stem
        
        # Bob claims it
        cmd_issue_claim(root, issue_id, operator="bob")
        issue = read_issue(root, issue_id)
        
        # Handler (bob) should be allowed to amend and transfer
        assert check_permission(root, "bob", "amend", issue=issue) is True
        assert check_permission(root, "bob", "transfer", issue=issue) is True
        
        # Handler (bob) should NOT be allowed to complete
        assert check_permission(root, "bob", "complete", issue=issue) is False

def test_v1_9_1_issue_show_format(capsys):
    from mai.config import GLOBAL
    GLOBAL.format = "text"
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        setup_project(root)
        
        cmd_issue_new(root, "questions", "Test Format", ref=None, operator="alice")
        issue_id = list((root / ".mai" / "queues" / "questions").glob("*.md"))[0].stem
        cmd_issue_claim(root, issue_id, operator="bob")
        
        capsys.readouterr()
        cmd_issue_show(root, issue_id)
        captured = capsys.readouterr()
        
        assert "Owner:    alice" in captured.out
        assert "Handler:  bob" in captured.out
