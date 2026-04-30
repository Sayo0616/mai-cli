import pytest
import os
import json
import sys
from pathlib import Path
from unittest.mock import patch
from io import StringIO
from mai.mai import main

@pytest.fixture
def temp_env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    
    with patch("pathlib.Path.home", return_value=home), \
         patch("os.getcwd", return_value=str(project)), \
         patch("mai.config.find_project_root", return_value=project):
        
        # Setup global root
        global_config_dir = home / ".mai-cli"
        global_config_dir.mkdir(mode=0o700)
        with open(global_config_dir / "config.json", "w") as f:
            json.dump({"root": ["admin"]}, f)
            
        yield {"home": home, "project": project}

def run_mai(args):
    stdout = StringIO()
    stderr = StringIO()
    with patch("sys.stdout", stdout), patch("sys.stderr", stderr), patch("sys.argv", ["mai"] + args):
        try:
            main()
        except SystemExit as e:
            if e.code != 0:
                return False, stdout.getvalue() + stderr.getvalue()
    return True, stdout.getvalue() + stderr.getvalue()

def test_project_init_and_duplicate(temp_env):
    # Should fail if not root
    ok, output = run_mai(["project", "init", "-o", "user"])
    assert not ok
    assert "权限不足" in output
    
    # Should succeed if root
    ok, output = run_mai(["project", "init", "-o", "admin"])
    assert ok
    assert "initialized" in output.lower()
    
    # Should fail if already initialized
    ok, output = run_mai(["project", "init", "-o", "admin"])
    assert not ok
    assert "已经初始化" in output

def test_issue_discard(temp_env):
    # Init project
    run_mai(["project", "init", "-o", "admin"])
    
    # Create issue
    ok, output = run_mai(["issue", "new", "requests", "Test Issue", "-o", "admin"])
    assert ok
    # Extraction: Issue FIX-84B82C created ...
    import re
    m = re.search(r"Issue ([A-Z0-9-]+) created", output)
    assert m, f"Could not find Issue ID in output: {output}"
    issue_id = m.group(1)
    
    # Discard by non-owner should fail
    ok, output = run_mai(["issue", "discard", issue_id, "Bad issue", "-o", "user"])
    assert not ok
    assert "权限不足" in output
    
    # Discard by root should succeed
    ok, output = run_mai(["issue", "discard", issue_id, "Bad issue", "-o", "admin"])
    assert ok
    assert "discarded" in output.lower()
    
    # Check status
    ok, output = run_mai(["issue", "show", issue_id])
    assert "DISCARDED" in output

def test_project_list_and_delete(temp_env):
    # Init
    run_mai(["project", "init", "-o", "admin"])
    
    # List
    ok, output = run_mai(["project", "list"])
    assert ok
    assert "project" in output
    
    # List by agent
    ok, output = run_mai(["project", "list", "--agent", "default"])
    assert ok
    assert "project" in output
    
    # Delete by non-root should fail
    ok, output = run_mai(["project", "delete", "project", "-o", "user"])
    assert not ok
    assert "权限不足" in output
    
    # Delete by root should succeed
    ok, output = run_mai(["project", "delete", "project", "-o", "admin"])
    assert ok
    assert "deleted successfully" in output
    
    # Check if directory is gone
    assert not temp_env["project"].exists()
    
    # Check registry is empty
    ok, output = run_mai(["project", "list"])
    assert "(None)" in output
