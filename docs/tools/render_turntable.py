#!/usr/bin/env python
"""Render 180-degree turntable frames of reconstructed point clouds for the
LIST3R project webpage.

Handles both ASCII and binary_little_endian PLY files with x,y,z,red,green,blue.
Downsamples to a target point budget, auto-orients the scene, and renders a
sequence of frames spanning 180 degrees of azimuth using matplotlib.
"""
import os
import sys
import struct
import argparse
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ----------------------------------------------------------------------------
# PLY loading
# ----------------------------------------------------------------------------
def _parse_header(f):
    """Read PLY header from a binary file handle. Returns (fmt, n_vertices,
    props, header_len). props is a list of (name, type) for the vertex element."""
    line = f.readline()
    if line.strip() != b"ply":
        raise ValueError("Not a PLY file")
    fmt = None
    n_vertices = 0
    props = []
    in_vertex = False
    while True:
        line = f.readline()
        if not line:
            raise ValueError("Unexpected EOF in header")
        s = line.strip()
        if s.startswith(b"format"):
            fmt = s.split()[1].decode()
        elif s.startswith(b"element"):
            parts = s.split()
            name = parts[1].decode()
            count = int(parts[2])
            in_vertex = (name == "vertex")
            if in_vertex:
                n_vertices = count
        elif s.startswith(b"property") and in_vertex:
            parts = s.split()
            ptype = parts[1].decode()
            pname = parts[-1].decode()
            props.append((pname, ptype))
        elif s == b"end_header":
            break
    return fmt, n_vertices, props, f.tell()


_NP_TYPE = {
    "float": np.float32, "float32": np.float32,
    "double": np.float64, "float64": np.float64,
    "uchar": np.uint8, "uint8": np.uint8, "char": np.int8, "int8": np.int8,
    "ushort": np.uint16, "uint16": np.uint16, "short": np.int16, "int16": np.int16,
    "uint": np.uint32, "uint32": np.uint32, "int": np.int32, "int32": np.int32,
}


def load_ply(path, max_points=300000, seed=0):
    """Load a PLY file, returning (xyz [N,3] float32, rgb [N,3] float in 0..1).
    Randomly subsamples to at most max_points."""
    with open(path, "rb") as f:
        fmt, n, props, header_end = _parse_header(f)
        names = [p[0] for p in props]
        has_rgb = all(c in names for c in ("red", "green", "blue"))

        if fmt == "ascii":
            col = {nm: i for i, (nm, _) in enumerate(props)}
            # Stream the file and keep only every `stride`-th line so huge
            # ASCII clouds (tens of millions of points) load in seconds.
            stride = max(1, n // max(1, max_points))
            kept = []
            idx = 0
            leftover = b""
            CHUNK = 8 * 1024 * 1024
            while True:
                buf = f.read(CHUNK)
                if not buf:
                    break
                buf = leftover + buf
                nl = buf.rfind(b"\n")
                if nl == -1:
                    leftover = buf
                    continue
                leftover = buf[nl + 1:]
                lines = buf[:nl].split(b"\n")
                for ln in lines:
                    if idx % stride == 0 and ln:
                        kept.append(ln)
                    idx += 1
            if leftover.strip():
                if idx % stride == 0:
                    kept.append(leftover.strip())
            text = b"\n".join(kept)
            # Parse the kept lines in one shot.
            from io import BytesIO
            data = np.loadtxt(BytesIO(text), dtype=np.float64)
            if data.ndim == 1:
                data = data[None, :]
            xyz = data[:, [col["x"], col["y"], col["z"]]].astype(np.float32)
            if has_rgb:
                rgb = data[:, [col["red"], col["green"], col["blue"]]].astype(np.float32) / 255.0
            else:
                rgb = None
        else:
            dtype = np.dtype([(nm, _NP_TYPE[tp]) for nm, tp in props])
            if fmt == "binary_big_endian":
                dtype = dtype.newbyteorder(">")
            arr = np.fromfile(f, dtype=dtype, count=n)
            xyz = np.stack([arr["x"], arr["y"], arr["z"]], axis=1).astype(np.float32)
            if has_rgb:
                rgb = np.stack([arr["red"], arr["green"], arr["blue"]], axis=1).astype(np.float32) / 255.0
            else:
                rgb = None

    # Drop non-finite.
    finite = np.isfinite(xyz).all(axis=1)
    xyz = xyz[finite]
    if rgb is not None:
        rgb = rgb[finite]

    if len(xyz) > max_points:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(xyz), size=max_points, replace=False)
        xyz = xyz[idx]
        if rgb is not None:
            rgb = rgb[idx]

    if rgb is None:
        rgb = np.full((len(xyz), 3), 0.6, dtype=np.float32)
    return xyz, rgb


# ----------------------------------------------------------------------------
# Orientation / cleaning
# ----------------------------------------------------------------------------
def clean_and_orient(xyz, rgb, pct=1.0, canonical=True):
    """Robustly center the cloud and clip outliers by percentile, so that
    sparse stray points (common in CUT3R/TTT3R drift) do not blow up the view.
    Optionally apply a PCA canonical orientation so that different methods'
    coordinate frames are shown upright and consistently."""
    # Robust center.
    center = np.median(xyz, axis=0)
    xyz = xyz - center

    # Clip per-axis to robust percentile range to ignore extreme outliers when
    # framing the view (points themselves kept, just used for limits later).
    lo = np.percentile(xyz, pct, axis=0)
    hi = np.percentile(xyz, 100 - pct, axis=0)
    keep = np.all((xyz >= lo - 1e-6) & (xyz <= hi + 1e-6), axis=1)
    # Keep at least 70% of points; if clipping is too aggressive, relax.
    if keep.mean() < 0.7:
        keep = np.ones(len(xyz), dtype=bool)
    xyz = xyz[keep]
    rgb = rgb[keep]

    if canonical:
        # PCA: room floor plane spans the two largest principal axes; the
        # smallest-variance axis is the vertical (up). Re-express points so the
        # two big axes become horizontal (plot X,Y) and up becomes plot Z.
        xyz = xyz - xyz.mean(axis=0)
        cov = np.cov(xyz.T)
        evals, evecs = np.linalg.eigh(cov)  # ascending eigenvalues
        # Columns ordered small->large; want [big, mid, small] -> X,Y,Z(up).
        order = [2, 1, 0]
        R = evecs[:, order]
        # Ensure right-handed.
        if np.linalg.det(R) < 0:
            R[:, 0] = -R[:, 0]
        xyz = xyz @ R

    # Scale to unit-ish so all scenes render at a comparable size.
    scale = np.percentile(np.linalg.norm(xyz, axis=1), 95)
    if scale > 0:
        xyz = xyz / scale
    return xyz, rgb


def render_turntable(xyz, rgb, out_dir, n_frames=36, az_start=-90, az_end=90,
                     elev=-70, point_size=1.2, dpi=100, figsize=4.2,
                     prefix="frame"):
    """Render n_frames spanning [az_start, az_end] azimuth."""
    os.makedirs(out_dir, exist_ok=True)
    azimuths = np.linspace(az_start, az_end, n_frames)
    lim = 1.4

    for i, az in enumerate(azimuths):
        fig = plt.figure(figsize=(figsize, figsize), dpi=dpi)
        ax = fig.add_subplot(111, projection="3d")
        ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2],
                   c=rgb, s=point_size, marker=".", linewidths=0,
                   edgecolors="none", depthshade=False)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_zlim(-lim, lim)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=az)
        ax.set_axis_off()
        # Pure white background, baked into the PNG (independent of page theme).
        ax.set_facecolor("white")
        fig.patch.set_facecolor("white")
        plt.subplots_adjust(left=0, right=1, bottom=0, top=1)
        out = os.path.join(out_dir, f"{prefix}_{i:02d}.png")
        fig.savefig(out, facecolor="white", dpi=dpi)
        plt.close(fig)
    return n_frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ply", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-points", type=int, default=250000)
    ap.add_argument("--frames", type=int, default=36)
    ap.add_argument("--elev", type=float, default=-70)
    ap.add_argument("--psize", type=float, default=1.2)
    ap.add_argument("--prefix", default="frame")
    args = ap.parse_args()

    print(f"Loading {args.ply} ...", flush=True)
    xyz, rgb = load_ply(args.ply, max_points=args.max_points)
    print(f"  {len(xyz)} points after subsample", flush=True)
    xyz, rgb = clean_and_orient(xyz, rgb)
    n = render_turntable(xyz, rgb, args.out, n_frames=args.frames,
                         elev=args.elev, point_size=args.psize, prefix=args.prefix)
    print(f"  wrote {n} frames to {args.out}", flush=True)


if __name__ == "__main__":
    main()
