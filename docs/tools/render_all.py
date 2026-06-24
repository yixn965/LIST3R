#!/usr/bin/env python
"""Batch-render 180-degree turntables for all methods x scenes used in the
LIST3R webpage, and emit a JSON manifest the page reads.

Run with the gaoj env python:
  /opt/data/private/gaoj/env/bin/python render_all.py
"""
import os
import json
import glob
import traceback

import render_turntable as rt

ROOT = "/opt/data/private/gaoj/3d_recon"
OUT_ROOT = "/opt/data/private/gaoj/3d_recon/VGGT-Long-main/list3r/webpage/assets/turntable"

N_FRAMES = 30
MAX_POINTS = 200000
ELEV = 22
PSIZE = 1.1

# Display order = quality narrative (streaming -> submap -> ours).
METHODS = ["CUT3R", "TTT3R", "VGGT-Long", "Scal3R", "Pi-Long", "LIST3R"]

# Scenes featured on the page. Each maps to a friendly label plus the dataset
# folder names used by each method family (names differ across pipelines).
#   vl   = name under VGGT-Long-main/{exps_pi3_2, exps_pi-long-baseline, exps}
#   ttt  = folder under TTT3R/output_dir2
#   scal = folder under Scal3R/outputs
SCENES = [
    {
        "id": "tum_kidnap", "label": "TUM fr2/360 kidnap",
        "vl": "TUM_rgbd_dataset_freiburg2_360_kidnap_rgb",
        "ttt": "TUM_rgbd_dataset_freiburg2_360_kidnap_rgb",
        "scal": "rgbd_dataset_freiburg2_360_kidnap",
    },
    {
        "id": "bonn_box", "label": "BONN placing box",
        "vl": "rgbd_bonn_dataset_rgbd_bonn_placing_obstructing_box_rgb",
        "ttt": "rgbd_bonn_dataset_rgbd_bonn_placing_obstructing_box_rgb",
        "scal": "rgbd_bonn_placing_obstructing_box",
    },
    {
        "id": "f3_sitting_xyz", "label": "TUM fr3 sitting xyz",
        "vl": "sequences_rgbd_dataset_freiburg3_sitting_xyz_rgb",
        "ttt": "sequences_rgbd_dataset_freiburg3_sitting_xyz_rgb",
        "scal": "rgbd_dataset_freiburg3_sitting_xyz",
    },
    {
        "id": "large_loop", "label": "Large Loop",
        "vl": "test_large_loop_2_rgb",
        "ttt": "test_large_loop_2_rgb",
        "scal": "large_loop_2",
    },
]


def first(pattern):
    hits = sorted(glob.glob(pattern))
    return hits[0] if hits else None


def ply_path(method, scene):
    """Resolve the point-cloud PLY for a given method + scene dict."""
    vl, ttt, scal = scene["vl"], scene["ttt"], scene["scal"]
    if method == "LIST3R":
        return first(f"{ROOT}/VGGT-Long-main/exps_pi3_2/{vl}/*/pcd/combined_pcd.ply")
    if method == "Pi-Long":
        return first(f"{ROOT}/VGGT-Long-main/exps_pi-long-baseline/{vl}/*/pcd/combined_pcd.ply")
    if method == "VGGT-Long":
        return first(f"{ROOT}/VGGT-Long-main/exps/{vl}/*/pcd/combined_pcd.ply")
    if method == "Scal3R":
        return first(f"{ROOT}/Scal3R/outputs/{scal}/points/whole.ply")
    if method == "TTT3R":
        return first(f"{ROOT}/TTT3R/output_dir2/{ttt}/*ttt3r*/ply/scene.ply")
    if method == "CUT3R":
        return first(f"{ROOT}/TTT3R/output_dir2/{ttt}/*cut3r*/ply/scene.ply")
    return None


def main():
    manifest = {"n_frames": N_FRAMES, "methods": METHODS, "scenes": []}
    for scene in SCENES:
        sid, label = scene["id"], scene["label"]
        scene_entry = {"id": sid, "label": label, "methods": {}}
        for method in METHODS:
            p = ply_path(method, scene)
            if not p or not os.path.exists(p):
                print(f"[skip] {sid}/{method}: no ply")
                continue
            out_dir = os.path.join(OUT_ROOT, sid, method)
            done = len(glob.glob(os.path.join(out_dir, "frame_*.png")))
            if done >= N_FRAMES:
                print(f"[have] {sid}/{method}: {done} frames")
                scene_entry["methods"][method] = True
                continue
            try:
                print(f"[render] {sid}/{method} <- {p}", flush=True)
                xyz, rgb = rt.load_ply(p, max_points=MAX_POINTS)
                xyz, rgb = rt.clean_and_orient(xyz, rgb)
                rt.render_turntable(xyz, rgb, out_dir, n_frames=N_FRAMES,
                                    elev=ELEV, point_size=PSIZE)
                scene_entry["methods"][method] = True
            except Exception:
                print(f"[error] {sid}/{method}")
                traceback.print_exc()
        if scene_entry["methods"]:
            manifest["scenes"].append(scene_entry)

    mpath = os.path.join(OUT_ROOT, "manifest.json")
    os.makedirs(OUT_ROOT, exist_ok=True)
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written to {mpath}")


if __name__ == "__main__":
    main()
