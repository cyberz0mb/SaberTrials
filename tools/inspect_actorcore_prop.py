"""Read-only FBX prop assessment in a factory-startup Blender process.

Only reports and optional preview renders are written; never saves source FBX or blend.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matrix(value):
    return [[float(x) for x in row] for row in value]


def node_inputs(node):
    result = {}
    for socket in node.inputs:
        if not hasattr(socket, "default_value"):
            continue
        value = socket.default_value
        if isinstance(value, (float, int, str, bool)):
            result[socket.name] = value
        elif hasattr(value, "__len__"):
            try:
                result[socket.name] = [float(v) for v in value]
            except (TypeError, ValueError):
                pass
    return result


def bounds(points):
    points = list(points)
    if not points:
        return None
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    return {"min": low, "max": high, "size": [high[i]-low[i] for i in range(3)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    if bpy.app.version[:2] != (5, 2):
        raise RuntimeError(f"Blender 5.2 required, got {bpy.app.version_string}")
    source = Path(args.source).resolve()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    original = {str(p.relative_to(source.parent)): digest(p) for p in source.parent.rglob("*") if p.is_file()}
    metadata = json.loads(source.with_suffix(".json").read_text(encoding="utf-8-sig"))
    report = {"source": str(source), "blender_version": bpy.app.version_string,
              "import": "factory-startup; default FBX import, global_scale=1.0; no saved blend",
              "source_files_before": original, "source_json": metadata}
    # FBX source axis/unit metadata, before importer coordinate conversion.
    from io_scene_fbx import parse_fbx
    root, version = parse_fbx.parse(str(source))
    report["fbx_version"] = version
    settings = next((e for e in root.elems if e.id == b"GlobalSettings"), None)
    def scalar(v):
        return v.decode("utf-8", errors="replace") if isinstance(v, bytes) else v
    report["fbx_global_settings"] = {}
    if settings:
        for group in settings.elems:
            if group.id == b"Properties70":
                for prop in group.elems:
                    if prop.id == b"P":
                        vals = [scalar(p) for p in prop.props]
                        report["fbx_global_settings"][vals[0]] = vals[4:]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(source), global_scale=1.0)
    scene = bpy.context.scene
    scene.frame_set(scene.frame_start)
    imported = list(scene.objects)
    meshes = [obj for obj in imported if obj.type == "MESH"]
    report["scene_units"] = {"system": scene.unit_settings.system, "scale_length": scene.unit_settings.scale_length}
    report["frame_range"] = [scene.frame_start, scene.frame_end]
    report["objects"] = []
    world_points = []
    for obj in imported:
        record = {"name": obj.name, "type": obj.type, "parent": obj.parent.name if obj.parent else None,
                  "parent_type": obj.parent_type, "parent_bone": obj.parent_bone,
                  "matrix_world": matrix(obj.matrix_world), "location": list(obj.location),
                  "rotation_euler": list(obj.rotation_euler), "scale": list(obj.scale),
                  "constraints": [c.type for c in obj.constraints],
                  "animation_action": obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None}
        if obj.type == "MESH":
            mesh = obj.data
            mesh.calc_loop_triangles()
            points = [obj.matrix_world @ v.co for v in mesh.vertices]
            world_points += points
            record.update(vertices=len(mesh.vertices), polygons=len(mesh.polygons), triangles=len(mesh.loop_triangles),
                          uv_layers=[u.name for u in mesh.uv_layers], world_bounds=bounds(points),
                          local_bounds=bounds(v.co for v in mesh.vertices),
                          shape_keys=[k.name for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
                          modifiers=[{"name": m.name, "type": m.type, "object": m.object.name if hasattr(m,"object") and m.object else None} for m in obj.modifiers],
                          materials=[])
            for i, slot in enumerate(obj.material_slots):
                polys = [p for p in mesh.polygons if p.material_index == i]
                verts = set(v for p in polys for v in p.vertices)
                record["materials"].append({"slot": i, "name": slot.material.name if slot.material else None,
                                            "polygons": len(polys), "triangles": sum(len(p.vertices)-2 for p in polys),
                                            "world_bounds": bounds(obj.matrix_world @ mesh.vertices[v].co for v in verts)})
            record["vertex_groups"] = []
            for group in obj.vertex_groups:
                members = [(v.index,g.weight) for v in mesh.vertices for g in v.groups if g.group == group.index and g.weight>0]
                record["vertex_groups"].append({"name": group.name, "vertices": len(members),
                                                "weight_min": min((w for _,w in members), default=0),
                                                "weight_max": max((w for _,w in members), default=0),
                                                "world_bounds": bounds(points[i] for i,_ in members)})
        if obj.type == "ARMATURE":
            record["bones"] = [{"name": b.name, "parent": b.parent.name if b.parent else None,
                                "head": list(b.head_local), "tail": list(b.tail_local),
                                "matrix_local": matrix(b.matrix_local), "use_deform": b.use_deform} for b in obj.data.bones]
        report["objects"].append(record)
    report["world_bounds"] = bounds(world_points)
    report["total_triangles"] = sum(len(o.data.loop_triangles) for o in meshes)
    report["materials"] = []
    for mat in bpy.data.materials:
        if not any(mat == slot.material for obj in meshes for slot in obj.material_slots):
            continue
        rec = {"name": mat.name, "diffuse_color": list(mat.diffuse_color), "metallic": mat.metallic,
               "roughness": mat.roughness, "nodes": [], "links": []}
        if mat.use_nodes:
            for n in mat.node_tree.nodes:
                rec["nodes"].append({"name": n.name, "type": n.type,
                                     "image": n.image.filepath if n.type == "TEX_IMAGE" and n.image else None,
                                     "inputs": node_inputs(n)})
            rec["links"] = [{"from": f"{l.from_node.name}.{l.from_socket.name}","to": f"{l.to_node.name}.{l.to_socket.name}"} for l in mat.node_tree.links]
        report["materials"].append(rec)
    report["actions"] = [{"name": a.name,"frame_range": list(a.frame_range),"slots": [s.identifier for s in a.slots]} for a in bpy.data.actions]
    report["texture_files"] = []
    for path in sorted(source.parent.rglob("*")):
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".tga"):
            continue
        img = bpy.data.images.load(str(path), check_existing=True)
        report["texture_files"].append({"path":str(path.relative_to(source.parent)),"size_bytes":path.stat().st_size,"pixels":list(img.size),"channels":img.channels})
    if args.render:
        bb = report["world_bounds"]
        center = Vector([(bb["min"][i]+bb["max"][i])/2 for i in range(3)])
        span = max(bb["size"])
        major = bb["size"].index(span)
        # View perpendicular to the main length axis, leaving it vertical/horizontal naturally.
        direction = Vector((0.8,-1.4,0.25)) if major == 2 else Vector((0.5,-1.0,0.8))
        direction.normalize()
        camdata = bpy.data.cameras.new("CAM_Assessment")
        camera = bpy.data.objects.new("CAM_Assessment", camdata)
        scene.collection.objects.link(camera)
        camera.location = center + direction*span*2.2
        camera.rotation_euler = (center-camera.location).to_track_quat("-Z","Y").to_euler()
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = span*1.2
        scene.camera = camera
        for name, offset, energy, size in [("Key",(1,-2,2),600,2),("Fill",(-2,-1,0.5),350,2),("Rim",(0,2,1),800,1.5)]:
            data = bpy.data.lights.new(name,"AREA")
            light = bpy.data.objects.new(name,data)
            scene.collection.objects.link(light)
            light.location = center+Vector(offset)*span
            light.rotation_euler = (center-light.location).to_track_quat("-Z","Y").to_euler()
            data.energy = energy*span*span
            data.shape = "DISK"
            data.size = size*span
        scene.world.color = (0.08,0.08,0.08)
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 32
        scene.render.resolution_x = 1000
        scene.render.resolution_y = 1200
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(out/"saber-prop-import-preview.png")
        scene.view_settings.view_transform = "AgX"
        bpy.ops.render.render(write_still=True)
        report["render"] = {"path": scene.render.filepath, "materials": "unmodified FBX importer materials; no JSON material reconstruction", "geometry": "unmodified imported mesh"}
    after = {str(p.relative_to(source.parent)): digest(p) for p in source.parent.rglob("*") if p.is_file()}
    report["source_unchanged"] = after == original
    if after != original:
        raise RuntimeError("Source files changed during assessment")
    (out/"prop-inspection.json").write_text(json.dumps(report, indent=2),encoding="utf-8")
    print(json.dumps({"report":str(out/"prop-inspection.json"),"blender":report["blender_version"],"triangles":report["total_triangles"],"bounds":report["world_bounds"],"source_unchanged":True}))


if __name__ == "__main__":
    main()
