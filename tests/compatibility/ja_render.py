"""Link the release cgame objects into a local render-callback regression test."""
import subprocess
from pathlib import Path

from playback import ROOT

target=ROOT/"dist/compat/ja-render-test"
target.mkdir(parents=True,exist_ok=True)
release=ROOT/"dist/compat/ja-build"
source=ROOT/"dist/compat/ja-source"
objects=list((release/"codemp/cgame/cgamex86_64.dir/Release").glob("*.obj"))
assert objects
def quote(path):
    return '"'+path.as_posix()+'"'

includes=" ".join(quote(p) for p in [source/"codemp",source/"shared",release/"shared",source/"lib/gsl-lite/include"])
inputs="\n".join(quote(p) for p in objects if p.stem!="cg_players")
(target/"CMakeLists.txt").write_text(f"""cmake_minimum_required(VERSION 3.20)
project(JaClientRenderTest C CXX)
add_executable(ja_render {quote(Path(__file__).resolve().with_suffix(".c"))} {inputs})
target_compile_definitions(ja_render PRIVATE WIN64 NOMINMAX FINAL_BUILD _CGAME _CRT_SECURE_NO_WARNINGS)
target_include_directories(ja_render PRIVATE {includes})
set_target_properties(ja_render PROPERTIES LINKER_LANGUAGE CXX)
""")
subprocess.run(["cmake","-S",target,"-B",target/"build","-G","Visual Studio 18 2026","-A","x64"],check=True)
subprocess.run(["cmake","--build",target/"build","--config","Release","--target","ja_render"],check=True)
subprocess.run([target/"build/Release/ja_render.exe"],check=True)
