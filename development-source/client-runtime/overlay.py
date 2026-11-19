"""Independent client runtime fixes discovered by model performance testing."""
from pathlib import Path
import hashlib

def apply(source):
    for target,name,digest in [
      ('codemp/client/cl_st_controller.inc','st_controller_move.inc','26522354e11dc591ac41182135f244f1aa220da2d13b570b88a21541300fa823'),
      ('shared/sdl/st_controller.inc','st_controller_input.inc','a5b071f927c9103a661305c8d641f6267f847413f073055a6f1d19eff6171e48')]:
        path=Path(source)/target
        replacement=Path(__file__).with_name(name).read_bytes()
        current=path.read_bytes()
        if current==replacement:continue
        assert hashlib.sha256(current).hexdigest()==digest, 'Controller baseline changed: '+target
        path.write_bytes(replacement)
