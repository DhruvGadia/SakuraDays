"""Finish the daylight grade, then author and validate the Niagara petals."""
import os, runpy
from pathlib import Path
HERE=Path(__file__).resolve().parent
for stage in ('geometry','lighting'):
    os.environ['SAKURA_TOWN_STAGE']=stage
    runpy.run_path(str(HERE/'refine_japanese_town.py'),run_name='__main__')
runpy.run_path(str(HERE/'create_sakura_petals.py'),run_name='__main__')
