"""Validated shape revisions and cohesive actor-local material treatment."""
import os,runpy
from pathlib import Path
root=Path(__file__).resolve().parent
for script in ['import_house_variants.py','import_refined_trees.py']:
    runpy.run_path(str(root/script),run_name='__main__')
os.environ['SAKURA_TOWN_STAGE']='materials'
runpy.run_path(str(root/'refine_japanese_town.py'),run_name='__main__')
