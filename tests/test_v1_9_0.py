import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
import getpass
import shutil

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def setup_project(root: Path, roots=None):
    from mai.config import save_config, clear_config_cache
    clear_config_cache()
    mai_dir = root / ".mai"
    if not mai_dir.exists():
        mai_dir.mkdir()
    config = {
        "queues": {
            "questions": {"owner": "alice", "sla_minutes": 60},
            "dev": {"owner": "bob", "sla_minutes": 120}
        },
        "agents": {
            "alice": {"heartbeat_minutes": 30},
            "bob": {"heartbeat_minutes": 30},
            "charlie": {"heartbeat_minutes": 30}
        }
    }
    if roots:
        config["root"] = roots
    save_config(root, config)

def test_operator_signature_requirement(monkeypatch, capsys):
    from mai.issue import cmd_issue_new, read_issue
    from mai.mai import get_operator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        setup_project(root)
        
        # 1. No operator, no env -> should fail
        monkeypatch.delenv("MAI_OPERATOR", raising=False)
        monkeypatch.delenv("MAI_AGENT", raising=False)
        monkeypatch.delenv("AGENT_NAME", raising=False)
        
        class MockArgs:
            operator = None
        
        with pytest.raises(SystemExit):
            get_operator(MockArgs())
        
        # 2. Provided via operator arg
        args = MockArgs()
        args.operator = "alice"
        assert get_operator(args) == "alice"
        
        # 3. Provided via MAI_OPERATOR env
        args.operator = None
        monkeypatch.setenv("MAI_OPERATOR", "bob")
        assert get_operator(args) == "bob"

def test_permission_matrix(monkeypatch):
    from mai.issue import cmd_issue_new, cmd_issue_claim, read_issue, check_permission
    from mai.lock import check_lock
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        setup_project(root, roots=["admin"])
        
        # alice is owner of 'questions'
        # root can do anything
        assert check_permission(root, "admin", "create", issue={"queue": "questions"}) is True
        assert check_permission(root, "alice", "create", issue={"queue": "questions"}) is True
        assert check_permission(root, "bob", "create", issue={"queue": "questions"}) is False
        
        # Create an issue
        cmd_issue_new(root, "questions", "Test Issue", ref=None, operator="alice")
        queue_dir = root / ".mai" / "queues" / "questions"
        issue_file = list(queue_dir.glob("*.md"))[0]
        issue_id = issue_file.stem
        issue = read_issue(root, issue_id)
        
        # alice is owner
        assert check_permission(root, "alice", "claim", issue=issue) is True
        # bob is registered agent, can claim
        assert check_permission(root, "bob", "claim", issue=issue) is True
        
        # bob claims it
        cmd_issue_claim(root, issue_id, operator="bob")
        li = check_lock(root, issue_id)
        assert li["holder"] == "bob"
        
        # Re-read issue to get current state (owner field in MD changes on claim)
        issue = read_issue(root, issue_id)
        assert issue["owner"] == "bob"
        
        # Handler (bob) can block/unblock
        assert check_permission(root, "bob", "block", issue=issue) is True
        assert check_permission(root, "bob", "unblock", issue=issue) is True
        
        # Handler (bob) CANNOT complete
        assert check_permission(root, "bob", "complete", issue=issue) is False
        # Owner (alice) CAN complete (even if not current handler)
        # Note: In REQ-B, owner = queue owner.
        assert check_permission(root, "alice", "complete", issue=issue) is True

def test_root_config():
    from mai.config import get_roots
    with tempfile.TemporaryDirectory() as tmpdir:
        root_path = Path(tmpdir)
        
        # 1. No root in config -> fallback to OS user
        setup_project(root_path)
        roots = get_roots(root_path)
        assert getpass.getuser() in roots
        
        # 2. Single root string
        shutil.rmtree(root_path / ".mai")
        setup_project(root_path, roots="sayo")
        assert get_roots(root_path) == ["sayo"]
        
        # 3. Multiple roots list
        shutil.rmtree(root_path / ".mai")
        setup_project(root_path, roots=["sayo", "admin"])
        assert get_roots(root_path) == ["sayo", "admin"]

def test_creator_to_owner_migration():
    from mai.issue import parse_issue_file
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        setup_project(root)
        
        # Simulate legacy v1.8 file with 发起方 but no 处理方
        content = (
            "# [REQ-1234] Legacy Issue\n"
            "\n"
            "**发起方：** @old_creator\n"
            "**优先级：** 🟢 P2\n"
            "**创建时间：** 2026-04-26T12:00:00\n"
            "**状态：** ⭕ OPEN\n"
            "**队列：** questions\n"
            "\n"
            "## 处理记录\n"
            "- [2026-04-26T12:00:00] @old_creator: 创建\n"
        )
        f = root / "legacy.md"
        f.write_text(content, encoding="utf-8")
        
        data = parse_issue_file(f)
        assert data["creator"] == "old_creator"
        assert data["owner"] == "old_creator" # Migrated

def test_confirm_alias(capsys):
    from mai.issue import cmd_issue_new, cmd_issue_claim, cmd_issue_confirm, read_issue
    from mai.lock import release_lock
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        setup_project(root)
        
        cmd_issue_new(root, "questions", "Test Confirm", ref=None, operator="alice")
        issue_id = list((root / ".mai" / "queues" / "questions").glob("*.md"))[0].stem
        
        # bob claims
        cmd_issue_claim(root, issue_id, operator="bob")
        
        # Simulate bob releasing the lock before alice confirms
        release_lock(root, issue_id)
        
        # alice (owner) confirms (alias to complete)
        cmd_issue_confirm(root, issue_id, operator="alice")
        
        issue = read_issue(root, issue_id)
        assert issue["status"] == "COMPLETED"
        assert any("已确认完成" in t for t in issue["timeline"])
