"""Apply geometry corrections and the validated Japanese storefront kit."""
import os, runpy
from pathlib import Path
script=Path(__file__).with_name('refine_japanese_town.py')
for stage in ('geometry','identity'):
    os.environ['SAKURA_TOWN_STAGE']=stage
    runpy.run_path(str(script),run_name='__main__')
