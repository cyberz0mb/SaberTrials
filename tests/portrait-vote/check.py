"""Native regression checks extracted from the actual candidate source; no server."""
from pathlib import Path
import argparse, json, subprocess, hashlib

ROOT = Path(__file__).resolve().parents[2]

def function(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    files = {name: a.source / name for name in (
        'engine/codemp/rd-rend2/tr_main.cpp',
        'game/codemp/game/g_cmds.c', 'game/codemp/game/g_sabertrials.c')}
    renderer = files['engine/codemp/rd-rend2/tr_main.cpp'].read_text()
    # Test the real viewport setup, stopping before projection/world traversal.
    viewport = function(renderer, 'void R_SetupViewParms(')
    viewport = viewport[:viewport.index('\n\ttr.viewParms.zNear')] + '\n}'
    vote = function(files['game/codemp/game/g_cmds.c'].read_text(), 'qboolean G_VoteGametype(')
    queue = function(files['game/codemp/game/g_sabertrials.c'].read_text(), 'void ST_QueueGametype(')
    template = (Path(__file__).parent / 'regression.cpp.in').read_text()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/'regression.cpp').write_text(template.replace('/* ACTUAL FUNCTIONS */', viewport+'\n'+vote+'\n'+queue))
    (a.out/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\nproject(PortraitVoteChecks LANGUAGES CXX)\nadd_executable(regression regression.cpp)\n')
    subprocess.run(['cmake','-S',str(a.out),'-B',str(a.out/'build'),'-G','Visual Studio 18 2026','-A','x64'],check=True)
    subprocess.run(['cmake','--build',str(a.out/'build'),'--config','Release'],check=True)
    r = subprocess.run([str(a.out/'build/Release/regression.exe')],capture_output=True,text=True)
    print(r.stdout)
    (a.out/'evidence.json').write_text(json.dumps({'passed':r.returncode==0,'map_or_server_started':False,
        'source':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()},
        'output':r.stdout, 'returncode':r.returncode},indent=2)+'\n')
    raise SystemExit(r.returncode)

if __name__ == '__main__': main()
