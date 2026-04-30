import pytest
import os
import json
import shutil
from pathlib import Path
from unittest.mock import patch
from io import StringIO

@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    
    # Clear environment variables
    monkeypatch.delenv("MAI_PROJECT", raising=False)
    monkeypatch.delenv("MAI_OPERATOR", raising=False)
    
    # Clear config cache
    from mai.config import clear_config_cache
    clear_config_cache()
    
    # We need to mock find_project_root to return our temp project
    with patch("pathlib.Path.home", return_value=home), \
         patch("os.getcwd", return_value=str(project)), \
         patch("mai.config.find_project_root", return_value=project), \
         patch("mai.mai.find_project_root", return_value=project), \
         patch("mai.project.find_project_root", return_value=project):
        
        # Setup global root
        global_config_dir = home / ".mai-cli"
        global_config_dir.mkdir(parents=True, mode=0o700)
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
            return True, stdout.getvalue()
        except SystemExit as e:
            return e.code == 0, stdout.getvalue() + stderr.getvalue()
        except Exception as e:
            return False, str(e)

def test_project_delete_should_only_delete_mai_files(temp_env):
    project_root = temp_env["project"]
    
    # 1. Init project
    ok, output = run_mai(["project", "init", "-o", "admin"])
    assert ok, f"Init failed: {output}"
    
    # 2. Add a non-mai file
    keep_file = project_root / "keep_me.txt"
    keep_file.write_text("don't delete me")
    
    # Verify .mai and async exist
    assert (project_root / ".mai").exists()
    assert (project_root / "async").exists()
    
    # 3. Delete project
    # Note: 'project' is the name of the directory which is used as project name in init
    ok, output = run_mai(["project", "delete", "project", "-o", "admin"])
    assert ok, f"Delete failed: {output}"
    
    # 4. Assertions
    assert not (project_root / ".mai").exists(), ".mai should be deleted"
    assert not (project_root / "async").exists(), "async should be deleted"
    
    # THIS IS THE EXPECTED BEHAVIOR AFTER FIX:
    # The project root and non-mai files should still exist.
    assert project_root.exists(), "Project root should STILL exist"
    assert keep_file.exists(), "Non-mai file should STILL exist"
    assert keep_file.read_text() == "don't delete me"
