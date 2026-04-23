import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

# Ensure the package is importable from src/
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_daily_summary_write_list_fix():
    from mai.daily_summary import daily_summary_trigger, daily_summary_write
    from mai.config import save_config
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / ".mai").mkdir()
        save_config(root, {
            "agents": {"coder": {}},
            "queues": {"q": {"handler": "coder"}},
            "daily_summary_order": ["coder"]
        })
        
        daily_summary_trigger(root)
        
        # Simulate list input from argparse
        content_list = ["fixed", "bug", "123"]
        daily_summary_write(root, "coder", content_list)
        
        today = datetime.now().strftime("%Y-%m-%d")
        summary_file = root / ".mai" / "history" / f"daily-{today}" / "coder.md"
        
        assert summary_file.exists()
        text = summary_file.read_text("utf-8")
        
        # Should be space separated, not literal list string representation
        assert "fixed bug 123" in text
        assert "['fixed', 'bug', '123']" not in text
