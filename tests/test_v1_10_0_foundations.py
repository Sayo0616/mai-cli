import pytest
import os
import json
import shutil
from pathlib import Path
from unittest.mock import patch
from mai.global_config import get_global_config_dir, get_global_config, save_global_config, get_global_roots
from mai.project_registry import add_project, remove_project, list_projects, list_projects_by_agent
from mai.permission import check_permission, check_project_permission, get_all_roots
from mai.config import GLOBAL

@pytest.fixture
def temp_home(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path

def test_global_config_dir_creation(temp_home):
    config_dir = get_global_config_dir()
    assert config_dir.exists()
    assert config_dir.name == ".mai-cli"
    # On POSIX, check permissions
    if os.name != 'nt':
        assert (config_dir.stat().st_mode & 0o777) == 0o700

def test_global_config_read_write(temp_home):
    config = {"root": ["alice", "bob"], "custom": "value"}
    save_global_config(config)
    
    loaded = get_global_config()
    assert loaded["root"] == ["alice", "bob"]
    assert loaded["custom"] == "value"
    assert "initialized_at" in loaded
    
    roots = get_global_roots()
    assert "alice" in roots
    assert "bob" in roots

def test_project_registry(temp_home):
    add_project("proj1", "/path/to/proj1", "Desc 1", ["agent1", "agent2"])
    add_project("proj2", "/path/to/proj2", "Desc 2", ["agent2", "agent3"])
    
    projects = list_projects()
    assert len(projects) == 2
    
    agent2_projs = list_projects_by_agent("agent2")
    assert len(agent2_projs) == 2
    
    agent1_projs = list_projects_by_agent("agent1")
    assert len(agent1_projs) == 1
    assert agent1_projs[0]["name"] == "proj1"
    
    remove_project("proj1")
    assert len(list_projects()) == 1
    assert list_projects()[0]["name"] == "proj2"

def test_permission_logic(temp_home, tmp_path):
    # Setup global root
    save_global_config({"root": ["admin"]})
    
    project_root = tmp_path / "myproj"
    project_root.mkdir()
    (project_root / ".mai").mkdir()
    
    # Test global root permission
    assert check_project_permission(project_root, "admin", "init") == True
    assert check_project_permission(project_root, "user", "init") == False
    
    # Test local owner permission
    # Mocking local config since we don't want to rely on full project init here
    local_config = {
        "queues": {
            "requests": {"handler": "programmer", "sla_minutes": 60, "id_prefix": "FIX"}
        },
        "agents": {"programmer": {}},
        "root": ["local_root"]
    }
    with open(project_root / ".mai" / "config.json", "w") as f:
        json.dump(local_config, f)
    
    # Clear cache to ensure reload
    from mai.config import clear_config_cache
    clear_config_cache()
    
    assert "local_root" in get_all_roots(project_root)
    assert check_project_permission(project_root, "local_root", "init") == True
    
    issue = {"queue": "requests", "owner": "someone_else"}
    # programmer is queue owner
    assert check_permission(project_root, "programmer", "discard", issue) == True
    # someone_else is issue handler
    assert check_permission(project_root, "someone_else", "amend", issue) == True
    assert check_permission(project_root, "someone_else", "discard", issue) == False
    
    # Global root can do anything
    assert check_permission(project_root, "admin", "discard", issue) == True
