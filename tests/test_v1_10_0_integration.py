import pytest
import os
import json
import sys
from pathlib import Path
from unittest.mock import patch
from io import StringIO
from mai.mai import main

@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    
    # Clear environment variables that might interfere
    monkeypatch.delenv("MAI_PROJECT", raising=False)
    monkeypatch.delenv("AGENTS_PROJECT", raising=False)
    monkeypatch.delenv("MAI_OPERATOR", raising=False)
    monkeypatch.delenv("MAI_AGENT", raising=False)
    monkeypatch.delenv("AGENT_NAME", raising=False)
    
    # Clear config cache
    from mai.config import clear_config_cache
    clear_config_cache()
    
    with patch("pathlib.Path.home", return_value=home), \
         patch("os.getcwd", return_value=str(project)), \
         patch("mai.config.find_project_root", return_value=project), \
         patch("mai.mai.find_project_root", return_value=project), \
         patch("mai.project.find_project_root", return_value=project):
        
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
            from mai.mai import main
            main()
        except SystemExit as e:
            if e.code != 0:
                return False, stdout.getvalue() + stderr.getvalue()
    return True, stdout.getvalue() + stderr.getvalue()

def test_project_init_and_duplicate(temp_env):
    # Should fail if not root
    ok, output = run_mai(["project", "init", "-o", "user"])
    assert not ok, f"Expected project init to fail for non-root user. Output: {output}"
    assert "权限不足" in output
    
    # Should succeed if root
    ok, output = run_mai(["project", "init", "-o", "admin"])
    assert ok, f"Project init failed for root user. Output: {output}"
    assert "initialized" in output.lower()
    
    # Should fail if already initialized
    ok, output = run_mai(["project", "init", "-o", "admin"])
    assert not ok, f"Expected project init to fail for already initialized project. Output: {output}"
    assert "已经初始化" in output

def test_issue_discard(temp_env):
    # Init project
    ok, output = run_mai(["project", "init", "-o", "admin"])
    assert ok, f"Project init failed in test_issue_discard. Output: {output}"
    
    # Create issue
    ok, output = run_mai(["issue", "new", "requests", "Test Issue", "-o", "admin"])
    assert ok, f"Issue creation failed. Output: {output}"
    # Extraction: Issue FIX-84B82C created ...
    import re
    m = re.search(r"Issue ([A-Z0-9-]+) created", output)
    assert m, f"Could not find Issue ID in output: {output}"
    issue_id = m.group(1)
    
    # Discard by non-owner should fail
    ok, output = run_mai(["issue", "discard", issue_id, "Bad issue", "-o", "user"])
    assert not ok, f"Expected issue discard to fail for non-root/non-owner. Output: {output}"
    assert "权限不足" in output
    
    # Discard by root should succeed
    ok, output = run_mai(["issue", "discard", issue_id, "Bad issue", "-o", "admin"])
    assert ok, f"Issue discard failed for root. Output: {output}"
    assert "discarded" in output.lower()
    
    # Check status
    ok, output = run_mai(["issue", "show", issue_id])
    assert ok, f"Issue show failed. Output: {output}"
    assert "DISCARDED" in output

def test_project_list_and_delete(temp_env):
    # Init
    ok, output = run_mai(["project", "init", "-o", "admin"])
    assert ok, f"Project init failed in test_project_list_and_delete. Output: {output}"
    
    # List
    ok, output = run_mai(["project", "list"])
    assert ok, f"Project list failed. Output: {output}"
    assert "project" in output.lower()
    
    # List by agent
    ok, output = run_mai(["project", "list", "--agent", "default"])
    assert ok, f"Project list by agent failed. Output: {output}"
    assert "project" in output.lower()
    
    # Delete by non-root should fail
    ok, output = run_mai(["project", "delete", "project", "-o", "user"])
    assert not ok, f"Expected project delete to fail for non-root. Output: {output}"
    assert "权限不足" in output
    
    # Delete by root should succeed
    ok, output = run_mai(["project", "delete", "project", "-o", "admin"])
    assert ok, f"Project delete failed for root. Output: {output}"
    assert "deleted successfully" in output.lower()
    
    # Check if directory is NOT gone (v1.10.4 change: only delete .mai/async)
    assert temp_env["project"].exists()
    assert not (temp_env["project"] / ".mai").exists()
    
    # Check registry is empty
    ok, output = run_mai(["project", "list"])
    assert ok, f"Project list failed after delete. Output: {output}"
    assert "(None)" in output
