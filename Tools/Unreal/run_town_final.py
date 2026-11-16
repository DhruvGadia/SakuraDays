"""Apply final saved placement corrections, then exercise the final scene in PIE."""
import os, runpy
from pathlib import Path
HERE=Path(__file__).resolve().parent
for stage in ('geometry','identity'):
    os.environ['SAKURA_TOWN_STAGE']=stage
    runpy.run_path(str(HERE/'refine_japanese_town.py'),run_name='__main__')
os.environ['SAKURA_TOWN_TEST_STAGE']='final'
runpy.run_path(str(HERE/'test_town_stage.py'),run_name='__main__')
