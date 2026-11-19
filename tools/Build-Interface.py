"""Build the UI-only cursor refinement using the pinned, accepted UI overlays."""
from pathlib import Path
import importlib.util
import tempfile

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('builder',ROOT/'tools/Build-Menu.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
builder.WORK=Path(tempfile.gettempdir())/'SaberTrials-interface-20261011'

if __name__=='__main__': builder.main()
