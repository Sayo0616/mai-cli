import pytest
import tempfile
import os
import sys
from unittest.mock import patch
from pathlib import Path
from mai.config import save_config, clear_config_cache, get_mai_dir
from mai.issue import cmd_issue_new, cmd_issue_discard, cmd_issue_transfer, read_issue
from mai.queue import cmd_queue_check
from mai.mai import build_parser, GLOBAL

@pytest.fixture
def temp_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".mai").mkdir()
        save_config(root, {
            "queues": {
                "dev": {"handler": "alice", "sla_minutes": 60}
            },
            "agents": {"alice": {}, "bob": {}},
            "root": ["alice", "bob"]
        })
        clear_config_cache()
        yield root

def get_issue_ids(project_root, queue):
    queue_dir = get_mai_dir(project_root) / "queues" / queue
    return [f.stem for f in queue_dir.glob("*.md")]

def test_v1_11_2_queue_check_terminology_and_filtering(temp_project, capsys):
    # 1. Create an issue
    cmd_issue_new(temp_project, "dev", "Issue 1", None, operator="alice")
    cmd_issue_new(temp_project, "dev", "Issue 2", None, operator="alice")
    
    ids = get_issue_ids(temp_project, "dev")
    id1, id2 = None, None
    for i in ids:
        iss = read_issue(temp_project, i)
        if iss["title"] == "Issue 1": id1 = i
        if iss["title"] == "Issue 2": id2 = i

    # 2. Discard Issue 2
    cmd_issue_discard(temp_project, id2, "Discarding for test", operator="alice")
    
    # Clear buffer
    capsys.readouterr()

    # 3. Check queue output
    GLOBAL.format = "text"
    cmd_queue_check(temp_project, "dev", overdue=False, show_all=False)
    out, err = capsys.readouterr()
    
    # Verify terminology: (handler: alice, ...)
    assert f"(handler: alice" in out
    assert f"(owner: alice" not in out
    
    # Verify filtering: Issue 2 (DISCARDED) should NOT be in output
    assert id1 in out
    assert id2 not in out
    
    # Verify show_all=True includes DISCARDED
    cmd_queue_check(temp_project, "dev", overdue=False, show_all=True)
    out_all, _ = capsys.readouterr()
    assert id1 in out_all
    assert id2 in out_all

def test_v1_11_2_transfer_mandatory_message(temp_project, capsys):
    cmd_issue_new(temp_project, "dev", "Issue 1", None, operator="alice")
    ids = get_issue_ids(temp_project, "dev")
    id1 = ids[0]
    
    parser = build_parser()
    
    # Try transfer without message - should raise SystemExit(1) via err()
    # Mock isatty to True to avoid reading from stdin in tests
    with patch("sys.stdin.isatty", return_value=True):
        with pytest.raises(SystemExit) as excinfo:
            args = parser.parse_args(["issue", "transfer", id1, "bob", "-o", "alice"])
            from mai.mai import dispatch_issue
            dispatch_issue(args, temp_project)
        assert excinfo.value.code == 1

    # Try transfer with message
    args = parser.parse_args(["issue", "transfer", id1, "bob", "Transferring for help", "-o", "alice"])
    from mai.mai import dispatch_issue
    dispatch_issue(args, temp_project)
    
    # Verify timeline remark
    issue = read_issue(temp_project, id1)
    found_remark = False
    for entry in issue.get("timeline", []):
        if f"转交给 @bob：Transferring for help" in entry.get("remark", ""):
            found_remark = True
            break
    assert found_remark, f"Transfer message not found in timeline."
    assert issue["owner"] == "bob"
