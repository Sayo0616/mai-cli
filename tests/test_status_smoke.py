import os
import tempfile
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mai.mai import cmd_status, GLOBAL

def test_cmd_status_smoke(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".mai").mkdir()
        (root / ".mai" / "config.json").write_text("{}", encoding="utf-8")
        (root / ".mai" / "queues").mkdir()
        (root / ".mai" / "locks").mkdir()
        (root / ".mai" / "daily-summary").mkdir()
        
        # Should not raise NameError or other exceptions
        cmd_status(root, verbose=True)
        
        captured = capsys.readouterr()
        assert "Project:" in captured.out
        assert "Queues:" in captured.out
        assert "Locks:" in captured.out
