import importlib.util
from pathlib import Path

import pandas as pd

spec = importlib.util.spec_from_file_location("sector_overlap", Path(__file__).parents[1] / "scripts" / "sector_overlap.py")
so = importlib.util.module_from_spec(spec)
spec.loader.exec_module(so)


def test_summarize_categories_and_cutoff():
    obs = pd.DataFrame({"target_name": ["1", "1", "2", "2", "3", "4"],
                        "sequence_number": [103, 102, 103, 12, 106, 94]})
    stats, per = so.summarize(obs, ["1", "2", "3", "4", "5"], 103)
    assert per["3"] == set()                      # 106 escluso (senza note di rilascio)
    assert stats["recent"] == 1 and stats["old"] == 2
    assert stats["year7"] == 1 and stats["years1_5"] == 1
    assert stats["any"] == 3 and stats["none"] == 2 and stats["both"] == 0
