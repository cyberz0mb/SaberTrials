"""Actual native menu-only lock probes. Never loads a map or game server.

Requires a matching native engine, renderer and QA UI with lock_qa.inc.
Geometry assertions use returned real *blade1 matrices, not solver outputs.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STYLES = ("single", "dual", "staff")
LABELS = ("baseline", "p0", "p05", "p1", "half", "zero", "relock",
          "clear", "relock2", "flip", "flipclear", "flipback", "finalclear")
LOCKED = {"p0", "p05", "p1", "relock", "relock2", "flip", "flipback"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dist(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def resolved_path(row, requested_first, requested_last, failures, key):
    # API v2 may lift the requested segment to clear the two actual seed bodies.
    # Do not derive the oracle from measured blade geometry: constrain both
    # returned endpoints independently, then compare the two actors' paths.
    # Twenty world units is a conservative bound for these Kyle .75..1.25
    # fixtures, not a production solver limit.
    if "first" not in row and "last" not in row:
        return requested_first, requested_last
    first, last = row.get("first"), row.get("last")
    if not isinstance(first, list) or not isinstance(last, list) or len(first) != 3 or len(last) != 3:
        failures.append(f"malformed resolved contact path {key}")
        return requested_first, requested_last
    lift = first[2]-requested_first[2]
    if (any(abs(got[i]-wanted[i]) > .001 for got, wanted in ((first, requested_first), (last, requested_last)) for i in (0, 1)) or
            abs(last[2]-requested_last[2]-lift) > .001 or not -.001 <= lift <= 20.001):
        failures.append(f"invalid resolved path displacement {key}: first={first}, last={last}")
    return first, last


def point_on_path(path, progress):
    return [a+(b-a)*progress for a, b in zip(*path)]


def make_plan(selected_cases=None, scale=1.):
    commands = ["wait 100", "set model kyle/default"]
    expected = []
    screenshots = []
    for case, (sa, sb, ha, hb, top) in enumerate(itertools.product(range(3), range(3), range(2), range(2), range(2))):
        if selected_cases is not None and case not in selected_cases:
            continue
        spacing = (32 if top else 48) if sa == sb == 0 else 46
        for actor in range(2):
            style, other = (sa, sb) if actor == 0 else (sb, sa)
            hand, otherhand = (ha, hb) if actor == 0 else (hb, ha)
            expected.append(dict(case=case, actor=actor, style=style, other=other,
                                 hand=hand, otherhand=otherhand, top=top, dist=spacing, scale=scale))
            commands += [f"st_handqa {STYLES[style]} {hand} 1", "wait 8",
                         f"st_lockqa seed {case} {style} {other} {hand} {otherhand} {top} {actor} {spacing} {scale}",
                         "wait 4", "st_lockqa probe baseline"]
            operations = [("update 0 1", "p0"), ("update 0.5 1", "p05"),
                          ("update 1 1", "p1"), ("update 1 0.5", "half"),
                          ("update 1 0", "zero"), ("update 0.5 1", "relock"),
                          ("clear", "clear"), ("update 0.5 1", "relock2"),
                          ("flip", "flip"), ("clear", "flipclear"),
                          ("flip", "flipback"), ("clear", "finalclear")]
            for operation, label in operations:
                # Separate mutation from evaluation by actual rendered UI frames.
                commands += [f"st_lockqa {operation}", "wait 4", f"st_lockqa probe {label}"]
                if label == "p05" and ha == 0 and hb == 1 and (actor == 0 or sa == sb):
                    name = f"lock-{STYLES[sa]}-{STYLES[sb]}-{'top' if top else 'side'}-actor{actor}-hand{hand}"
                    screenshots.append(name + ".png")
                    commands += [f"screenshot_png {name}", "wait 4"]
    commands += ["echo ST_LOCK_QA_COMPLETE", "quit"]
    return commands, expected, screenshots



def make_pair_plan(scale=1.):
    commands, scenes, screenshots = [], [], []
    for case, (sa, sb, ha, hb, top) in enumerate(itertools.product(range(3), range(3), range(2), range(2), range(2))):
        if sa > sb or ha == hb or (sa != sb and ha != 0):
            continue
        spacing = (32 if top else 48) if sa == sb == 0 else 46
        scenes.append(dict(case=case, styles=[sa, sb], hands=[ha, hb], top=top, dist=spacing, scale=scale))
        commands.append("st_lockqa pairreset")
        for actor in range(2):
            style, other = (sa, sb) if actor == 0 else (sb, sa)
            hand, otherhand = (ha, hb) if actor == 0 else (hb, ha)
            commands += [f"st_handqa {STYLES[style]} {hand} 1", "wait 8",
                         f"st_lockqa seed {case} {style} {other} {hand} {otherhand} {top} {actor} {spacing} {scale}",
                         "wait 4", f"st_lockqa paircapture {actor}", "wait 4"]
        commands += ["st_lockqa pairshow 0", "wait 12", "st_lockqa pairprobe"]
        for camera in (0, 1):
            name = f"pair-{case:02d}-{STYLES[sa]}-{ha}-{STYLES[sb]}-{hb}-{'top' if top else 'side'}-view{camera}"
            screenshots.append(name+".png")
            commands += [f"st_lockqa paircamera {camera}", "wait 4", f"screenshot_png {name}", "wait 4"]
    # Rend2 reads screenshot pixels back on a later GPU frame. Keep the final
    # scene alive long enough to finish its readback before clearing/quit.
    commands += ["wait 120", "st_lockqa pairreset", "echo ST_LOCK_PAIR_COMPLETE"]
    return commands, scenes, screenshots


def validate_pairs(log, scenes):
    failures, records, states = [], [], {}
    for line in log.splitlines():
        if "PAIR_QA " in line:
            fields = dict(re.findall(r"(\w+)=([^\s]+)", line.split("PAIR_QA ", 1)[1]))
            records.append({k: [float(x) for x in v.split(",")] if "," in v else float(v) for k, v in fields.items()})
        elif "PAIR_QA_STATE " in line:
            row = {k: int(v) for k, v in re.findall(r"(\w+)=([^\s]+)", line.split("PAIR_QA_STATE ", 1)[1])}
            states[row["case"]] = row
    index, max_perp = {}, 0.
    for row in records:
        key = tuple(int(row[k]) for k in ("case", "actor", "hilt", "blade"))
        if key in index:
            failures.append(f"duplicate paired scene blade {key}")
        index[key] = row
    for scene in scenes:
        state = states.get(scene["case"])
        if not state or state["drawn"] < 4 or state["visible"] != 1 or state["separate"] != 1:
            failures.append(f"pair scene not rendered with two separate models: {scene['case']}")
        for actor, (style, hand) in enumerate(zip(scene["styles"], scene["hands"])):
            for hilt in range(2 if style == 1 else 1):
                for blade in range(2 if style == 2 else 1):
                    key = (scene["case"], actor, hilt, blade)
                    row = index.get(key)
                    if row is None:
                        failures.append(f"missing paired scene blade {key}")
                        continue
                    if row.get("scale", 1.) != scene.get("scale", 1.):
                        failures.append(f"wrong actual paired model scale {key}")
                    if row["result"] != 1 or row["style"] != style or row["hand"] != hand or row["dist"] != scene["dist"]:
                        failures.append(f"wrong paired actor state {key}")
                    values = [v for value in row.values() for v in (value if isinstance(value, list) else [value])]
                    if not all(math.isfinite(v) for v in values):
                        failures.append(f"nonfinite paired geometry {key}")
                        continue
                    if abs(sum(v*v for v in row["direction"])-1) > .01:
                        failures.append(f"nonunit paired direction {key}")
                    if row.get("contacting", blade == 0):
                        path = resolved_path(row, [-4.,0.,32.], [4.,0.,32.], failures, key)
                        contact = point_on_path(path, row["progress"])
                        delta = [c-o for c, o in zip(contact, row["origin"])]
                        t = sum(v*d for v, d in zip(delta, row["direction"]))
                        perp = math.sqrt(sum((v-t*d)**2 for v, d in zip(delta, row["direction"])))
                        max_perp = max(max_perp, perp)
                        if perp > .2 or not .75 <= t <= row["length"]-.75:
                            failures.append(f"paired scene contact miss {key}: perpendicular={perp},t={t}")
    for scene in scenes:
        a, b = index.get((scene["case"],0,0,0)), index.get((scene["case"],1,0,0))
        if a and b and "first" in a and "first" in b:
            if dist(a["first"],b["first"]) > .001 or dist(a["last"],b["last"]) > .001:
                failures.append(f"independent paired scene paths disagree: {scene['case']}")
    expected = sum(sum(1 if style == 0 else 2 for style in scene["styles"]) for scene in scenes)
    if len(records) != expected:
        failures.append(f"paired scene blade count {len(records)} != {expected}")
    if scenes and "ST_LOCK_PAIR_COMPLETE" not in log:
        failures.append("paired scene completion missing")
    return dict(passed=not failures, failures=failures, scenes=len(scenes), blade_records=len(records),
                max_contact_perpendicular=max_perp, max_contact_lift=max((r.get("first",[0,0,32])[2]-32 for r in records),default=0), records=records)



def validate_fingers(log, expected, pair_scenes):
    rows, failures, wanted = {}, [], {}
    for item in expected:
        for label in LOCKED:
            for side in (0, 1):
                wanted[(item["case"], item["actor"], label, side)] = 1-item["hand"] if label == "flip" else item["hand"]
    for scene in pair_scenes:
        for actor in (0, 1):
            for side in (0, 1):
                wanted[(scene["case"], actor, "pair", side)] = scene["hands"][actor]
    for line in log.splitlines():
        if "FINGER_QA " not in line:
            continue
        fields = dict(re.findall(r"(\w+)=([^\s]+)", line.split("FINGER_QA ", 1)[1]))
        row = {k: v if k == "label" else float(v) for k, v in fields.items()}
        key = (int(row["case"]), int(row["actor"]), row["label"], int(row["side"]))
        if key in rows:
            failures.append(f"duplicate finger probe {key}")
        rows[key] = row
    for key, hand in wanted.items():
        row = rows.get(key)
        if row is None:
            failures.append(f"missing native finger/hilt probe {key}")
            continue
        if row["hand"] != hand or not math.isfinite(row["position"]) or not math.isfinite(row["orientation"]):
            failures.append(f"invalid finger/hilt probe state {key}")
        elif row["position"] > .05 or row["orientation"] > .005:
            failures.append(f"finger/hilt grip changed {key}: position={row['position']:.8f}, orientation={row['orientation']:.8f}")
    if len(rows) != len(wanted):
        failures.append(f"finger probe count {len(rows)} != {len(wanted)}")
    return dict(passed=not failures, failures=failures, records=len(rows),
                max_position_error=max((row["position"] for row in rows.values()),default=0),
                max_orientation_error=max((row["orientation"] for row in rows.values()),default=0))


def write_configs(mod, commands):
    # exec inserts into the finite engine command buffer. Chain bounded chunks.
    chunks, current, length = [], [], 0
    for line in commands:
        if current and length + len(line) + 1 > 6500:
            chunks.append(current)
            current, length = [], 0
        current.append(line)
        length += len(line) + 1
    if current:
        chunks.append(current)
    for i, chunk in enumerate(chunks):
        if i+1 < len(chunks):
            chunk.append(f"exec lock-qa-{i+1:03d}.cfg")
        (mod / f"lock-qa-{i:03d}.cfg").write_text("\n".join(chunk)+"\n")


def parse_records(log):
    records = []
    for line in log.splitlines():
        if "LOCK_QA " not in line:
            continue
        line = line.split("LOCK_QA ", 1)[1]
        row = {}
        for key, value in re.findall(r"(\w+)=([^\s]+)", line):
            row[key] = ([float(v) for v in value.split(",")] if "," in value else
                        value if key == "label" else float(value))
        records.append(row)
    return records


def validate(log, records, expected, screenshot_names, mod):
    failures = []
    if "ST_LOCK_QA_COMPLETE" not in log:
        failures.append("completion marker missing")
    if re.search(r"Server Initialization|SpawnServer|Loading map", log, re.I):
        failures.append("unexpected map/server activity")
    failures += [line for line in log.splitlines() if "LOCK_QA_ERROR" in line]
    index = {}
    for row in records:
        key = (int(row["case"]), int(row["actor"]), row["label"], int(row["hilt"]))
        if key in index:
            failures.append(f"duplicate probe {key}")
        index[key] = row
    max_perp, max_clear, max_norm_error = 0., 0., 0.
    counts = {"locked": 0, "clear": 0, "half_release": 0, "same_instance_flip": 0}
    for item in expected:
        n = 2 if item["style"] == 1 else 1
        for hilt in range(n):
            baseline = index.get((item["case"], item["actor"], "baseline", hilt))
            for label in LABELS:
                key = (item["case"], item["actor"], label, hilt)
                row = index.get(key)
                if row is None:
                    failures.append(f"missing probe {key}")
                    continue
                if row.get("scale", 1.) != item.get("scale", 1.):
                    failures.append(f"wrong actual model scale {key}")
                for field in ("style", "other", "otherhand", "top", "dist"):
                    if row[field] != item[field]:
                        failures.append(f"wrong {field} at {key}: {row[field]} != {item[field]}")
                wanted_hand = 1-item["hand"] if label in ("flip", "flipclear") else item["hand"]
                if row["hand"] != wanted_hand or row["result"] != 1:
                    failures.append(f"wrong hand or rejected API at {key}: hand={row['hand']} result={row['result']}")
                values = [v for value in row.values() for v in (value if isinstance(value, list) else [value]) if isinstance(v, (int, float))]
                if not all(math.isfinite(v) for v in values):
                    failures.append(f"nonfinite real geometry at {key}")
                    continue
                direction, origin = row["direction"], row["origin"]
                norm_error = abs(math.sqrt(sum(v*v for v in direction))-1)
                max_norm_error = max(max_norm_error, norm_error)
                if norm_error > .005:
                    failures.append(f"nonunit blade direction at {key}: {norm_error:.6f}")
                if label in LOCKED:
                    counts["locked"] += 1
                    if label == "flip":
                        counts["same_instance_flip"] += 1
                    if row["weight"] != 1 or row["mode"] != 1:
                        failures.append(f"inactive expected locked pose {key}")
                    if row.get("contacting", 1):
                        # Input spacing and permitted lift constrain the path;
                        # actual emitted blade matrices remain independent.
                        sign = -1 if item["actor"] else 1
                        path = resolved_path(row, [item["dist"]*.5-sign*4,0.,32.],
                                             [item["dist"]*.5+sign*4,0.,32.], failures, key)
                        contact = point_on_path(path, row["progress"])
                        delta = [c-o for c, o in zip(contact, origin)]
                        t = sum(x*y for x, y in zip(delta, direction))
                        perp = math.sqrt(sum((x-t*y)**2 for x, y in zip(delta, direction)))
                        max_perp = max(max_perp, perp)
                        if perp > .2 or not .75 <= t <= row["length"]-.75:
                            failures.append(f"contact miss {key}: perpendicular={perp:.6f}, t={t:.6f}, luminous=[0,{row['length']:.6f}]")
                        if dist(contact, row["contact"]) > .0001 or abs(perp-row["perp"]) > .002 or abs(t-row["t"]) > .002:
                            failures.append(f"reported geometry disagrees with independent calculation at {key}")
                if label in ("zero", "clear", "finalclear") and baseline:
                    counts["clear"] += 1
                    position_error = dist(origin, baseline["origin"])
                    direction_error = dist(direction, baseline["direction"])
                    max_clear = max(max_clear, position_error)
                    if position_error > .05 or direction_error > .002:
                        failures.append(f"clear failed to restore baseline {key}: position={position_error:.6f}, direction={direction_error:.6f}")
                if label == "half" and baseline:
                    full = index.get((item["case"], item["actor"], "p1", hilt))
                    if full:
                        counts["half_release"] += 1
                        full_delta = dist(full["origin"], baseline["origin"])+dist(full["direction"], baseline["direction"])
                        if full_delta > .1 and (dist(origin, full["origin"])+dist(direction, full["direction"]) < .001 or
                                                dist(origin, baseline["origin"])+dist(direction, baseline["direction"]) < .001):
                            failures.append(f"half release did not produce an intermediate pose at {key}")
    # Each actor was measured separately. Transform the real nearest blade
    # points into one shared pair space and compare them across both actors.
    max_pair_gap = 0.
    pair_checks = 0
    by_pair = {(item["case"], item["actor"]): item for item in expected}
    for case in sorted({item["case"] for item in expected}):
        left, right = by_pair.get((case, 0)), by_pair.get((case, 1))
        if left is None or right is None:
            continue
        for label in ("p0", "p05", "p1"):
            for ha in range(2 if left["style"] == 1 else 1):
                for hb in range(2 if right["style"] == 1 else 1):
                    a, b = index.get((case, 0, label, ha)), index.get((case, 1, label, hb))
                    if a is None or b is None or not a.get("contacting",1) or not b.get("contacting",1):
                        continue
                    points, paths = [], []
                    for actor, row in enumerate((a, b)):
                        sign = -1 if actor else 1
                        path = resolved_path(row, [left["dist"]*.5-sign*4,0.,32.],
                                             [left["dist"]*.5+sign*4,0.,32.], failures, (case,actor,label))
                        contact = point_on_path(path,row["progress"])
                        paths.append([[left["dist"]-v[0],-v[1],v[2]] for v in path] if actor else path)
                        t = sum((c-o)*d for c, o, d in zip(contact, row["origin"], row["direction"]))
                        point = [o+t*d for o, d in zip(row["origin"], row["direction"])]
                        if actor:
                            point = [left["dist"]-point[0], -point[1], point[2]]
                        points.append(point)
                    if dist(paths[0][0],paths[1][0]) > .001 or dist(paths[0][1],paths[1][1]) > .001:
                        failures.append(f"independent resolved pair paths disagree case={case} label={label}")
                    gap = dist(*points)
                    pair_checks += 1
                    max_pair_gap = max(max_pair_gap, gap)
                    if gap > .4:
                        failures.append(f"paired blade gap case={case} label={label} hilts={ha},{hb}: {gap:.6f}")
    counts["paired_contacts"] = pair_checks
    wanted_count = sum((2 if item["style"] == 1 else 1)*len(LABELS) for item in expected)
    if len(records) != wanted_count:
        failures.append(f"probe count {len(records)} != {wanted_count}")
    for name in screenshot_names:
        path = mod / "screenshots" / name
        if not path.exists() or path.stat().st_size < 1000:
            failures.append(f"missing or empty screenshot {name}")
    return dict(passed=not failures, failures=failures, scenarios=len(expected), records=len(records),
                checks=counts, max_contact_perpendicular=max_perp, max_contact_lift=max((r.get("first",[0,0,32])[2]-32 for r in records),default=0), max_pair_contact_gap=max_pair_gap, max_clear_position_error=max_clear,
                max_blade_direction_norm_error=max_norm_error,
                map_or_server_started=bool(re.search(r"Server Initialization|SpawnServer|Loading map", log, re.I)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--build-dir", "--build", dest="build_dir", type=Path,
                        default=ROOT/"dist/handedness-preview-build/Release",
                        help="Release directory containing the engine, selected renderer, and QA UI")
    parser.add_argument("--renderer", choices=("vanilla", "rend2"), default="vanilla")
    parser.add_argument("--stage-only", action="store_true")
    parser.add_argument("--pair-scenes", action="store_true", help="append simultaneous two-actor visual scenes")
    parser.add_argument("--pairs-only", action="store_true", help="run simultaneous scenes without repeating the measurement suite")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--scale", type=float, default=1., help="uniform character scale; world luminous blade lengths remain unchanged")
    parser.add_argument("--case", type=int, action="append", dest="cases", help="bounded diagnostic case 0..71; repeat to select more")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", args.tag):
        parser.error("tag must be a simple directory name")
    run = ROOT / "dist/verification/handedness-20261024" / args.tag
    mod, app = run / "home/SaberTrials", run / "bin"
    if args.cases is not None and any(case < 0 or case >= 72 for case in args.cases):
        parser.error("case must be in 0..71")
    if not math.isfinite(args.scale) or args.scale <= 0:
        parser.error("scale must be finite and positive")
    commands, expected, screenshots = make_plan(set(args.cases) if args.cases is not None else None, args.scale)
    pair_scenes = []
    finger_probe = True
    if args.pairs_only:
        commands, expected, screenshots = ["wait 100", "set model kyle/default", "st_handqa single 0 1", "wait 8"], [], []
    elif args.pair_scenes:
        commands = commands[:-2]
    if args.pair_scenes or args.pairs_only:
        pair_commands, pair_scenes, pair_screenshots = make_pair_plan(args.scale)
        commands += pair_commands + ["echo ST_LOCK_QA_COMPLETE", "quit"]
        screenshots += pair_screenshots
    if args.analyze_only:
        plan = json.loads((run/"plan.json").read_text())
        expected, screenshots = plan["scenarios"], plan["screenshots"]
        pair_scenes = plan.get("pair_scenes", [])
        finger_probe = plan.get("finger_probe", False)
        log = (mod / "qconsole.log").read_text(errors="replace")
    else:
        if run.exists():
            raise RuntimeError(f"Evidence directory already exists: {run}")
        build = args.build_dir.resolve()
        renderer_name = f"rd-{args.renderer}"
        required = [build/"openjk.x86_64.exe", build/f"{renderer_name}_x86_64.dll", build/"uix86_64.dll"]
        for path in required:
            if not path.is_file():
                raise RuntimeError(f"Required native QA binary missing: {path}")
        mod.mkdir(parents=True)
        app.mkdir()
        shutil.copy2(required[0], app/required[0].name)
        shutil.copy2(required[1], app/required[1].name)
        shutil.copy2(required[2], mod/required[2].name)
        for name in ("SDL2.dll", "OpenAL32.dll"):
            source = build/name if (build/name).exists() else ROOT/"client"/name
            shutil.copy2(source, app/name)
        menu = mod / "ui/jamp/saber.menu"
        menu.parent.mkdir(parents=True)
        original = (ROOT / "ui/jamp/saber.menu").read_text()
        end = original.rfind("}")
        menu.write_text(original[:end]+"\n"+(ROOT/"development-source/handedness/ui/handedness.menu").read_text()+"\n"+original[end:])
        write_configs(mod, commands)
        (run/"plan.json").write_text(json.dumps(dict(scenarios=expected, screenshots=screenshots, pair_scenes=pair_scenes, finger_probe=finger_probe), indent=2)+"\n")
        launch = [str(app/"openjk.x86_64.exe"), "+set", "fs_basepath", str(ROOT.parent),
                  "+set", "fs_homepath", str(run/"home"), "+set", "fs_game", "SaberTrials",
                  "+set", "r_fullscreen", "0", "+set", "r_mode", "-1",
                  "+set", "r_customwidth", "1280", "+set", "r_customheight", "800",
                  "+set", "cl_renderer", renderer_name, "+set", "s_initsound", "0",
                  "+set", "com_maxfps", "60", "+set", "logfile", "2",
                  "+set", "com_introplayed", "1", "+exec", "lock-qa-000.cfg"]
        manifest = {"build": str(build), "renderer": args.renderer, "launch": launch, "map_or_server_requested": False,
                    "files": {str(path.relative_to(run)): sha(path) for path in [app/required[0].name, app/required[1].name, mod/required[2].name]},
                    "sources": {str(path.relative_to(ROOT)): sha(path) for path in [ROOT/"tests/handedness/lock_qa.inc", Path(__file__).resolve()]}}
        (run/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
        if args.stage_only:
            print(f"Staged isolated menu probe: {run}")
            return 0
        startup = subprocess.STARTUPINFO()
        startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        proc = subprocess.Popen(launch, cwd=app, env=os.environ.copy(), startupinfo=startup,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Menu-only lock probe PID {proc.pid}; {len(expected)} actor scenarios; {len(pair_scenes)} paired scenes", flush=True)
        try:
            proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=10)
            raise RuntimeError(f"Menu probe timed out; evidence retained at {run}")
        log = (mod/"qconsole.log").read_text(errors="replace")
        (run/"process.json").write_text(json.dumps({"pid": proc.pid, "returncode": proc.returncode})+"\n")
    (run/"analysis_manifest.json").write_text(json.dumps({"checker_sha256": sha(Path(__file__).resolve()), "qconsole_sha256": sha(mod/"qconsole.log")}, indent=2)+"\n")
    records = parse_records(log)
    report = validate(log, records, expected, screenshots, mod)
    manifest = json.loads((run/"manifest.json").read_text())
    if "renderer" in manifest:
        wanted_renderer = f"rd-{manifest['renderer']}_x86_64.dll"
        loads = re.findall(r'Trying to load "(rd-[^"]+)" from "([^"]+)"', log)
        report["renderer"] = manifest["renderer"]
        report["renderer_loads"] = loads
        if not loads or any(name != wanted_renderer or Path(folder).resolve() != app.resolve()
                            for name, folder in loads):
            report["failures"].append(f"selected isolated renderer not exclusively loaded: {loads}")
            report["passed"] = False
    if pair_scenes:
        pair_report = validate_pairs(log, pair_scenes)
        (run/"pair_result.json").write_text(json.dumps(pair_report, indent=2)+"\n")
        report["pair_scenes"] = {k:v for k,v in pair_report.items() if k != "records"}
        report["failures"].extend(pair_report["failures"])
        report["passed"] = not report["failures"]
    if finger_probe:
        finger_report = validate_fingers(log, expected, pair_scenes)
        (run/"finger_result.json").write_text(json.dumps(finger_report, indent=2)+"\n")
        report["finger_grips"] = finger_report
        report["failures"].extend(finger_report["failures"])
        report["passed"] = not report["failures"]
    if not args.analyze_only and proc.returncode != 0:
        report["failures"].append(f"native process exit {proc.returncode}")
        report["passed"] = False
    report["screenshots"] = {name: sha(mod/"screenshots"/name) for name in screenshots if (mod/"screenshots"/name).exists()}
    (run/"measurements.json").write_text(json.dumps(records, indent=2)+"\n")
    (run/"result.json").write_text(json.dumps(report, indent=2)+"\n")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {len(records)} real blade probes; {len(report['failures'])} failures; evidence {run}")
    for failure in report["failures"][:12]:
        print(failure)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
