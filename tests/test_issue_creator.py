import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_issue_new_with_creator_override():
    from mai.issue import cmd_issue_new, parse_issue_file
    from mai.config import save_config
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".mai").mkdir()
        save_config(root, {
            "queues": {"questions": {"handler": "alice", "sla_minutes": 60}}
        })
        
        # Test 1: Override creator via parameter
        cmd_issue_new(root, "questions", "Test override", ref=None, creator="human_sayo")
        
        # Find the created file
        issue_file = next((root / ".mai" / "queues" / "questions").glob("*.md"))
        data = parse_issue_file(issue_file)
        
        assert data["creator"] == "human_sayo"
        assert "**发起方：** @human_sayo" in data["raw"]

def test_issue_new_default_creator(monkeypatch):
    from mai.issue import cmd_issue_new, parse_issue_file
    from mai.config import save_config
    
    # Mock environment variable
    monkeypatch.setenv("MAI_AGENT", "auto_coder")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".mai").mkdir()
        save_config(root, {
            "queues": {"questions": {"handler": "alice", "sla_minutes": 60}}
        })
        
        # Test 2: Fallback to environment variable
        cmd_issue_new(root, "questions", "Test default", ref=None)
        
        issue_file = next((root / ".mai" / "queues" / "questions").glob("*.md"))
        data = parse_issue_file(issue_file)
        
        assert data["creator"] == "auto_coder"
