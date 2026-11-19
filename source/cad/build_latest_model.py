"""Integrate the latest STL model (Lipat Baju.stl) into the project.

- Resizes ONLY the folding board to match the previous Rev B envelope:
  630.0 mm (width) x 540.0 mm (length) x 8.0 mm (height; 4.0 mm plate + 0.8 mm Braille + 8.0 mm hinges).
- Keeps the new control box housing, screw tabs, lid, and tactile symbols at
  their exact 1:1 original dimensions, seated flush together.
- Splits the folding board along its 3 hinge centerlines so Left Wing, Right Wing,
  and Bottom Flap articulate cleanly in the offline WebGL 2 web preview.
- Exports print-ready right-handed STL files to Web Preview/stl_terbaru and
  output/cad_rev_b/stl_terbaru.
- Builds Web Preview/index.html and output/cad_rev_b/COBA_MEKANISME.html with
  both the latest model (default) and the previous Rev B design.
"""
from pathlib import Path
import sys
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cad_runtime'))

import numpy as np
import trimesh

SOURCE_STL = Path(r'c:\Users\User\Downloads\Lipat Baju.stl')
REPO_SOURCE_STL = ROOT / 'cad' / 'Lipat Baju.stl'
WEB_DIR = ROOT / 'Web Preview'
OUT_DIR = ROOT / 'output' / 'cad_rev_b'

# Target Rev B board dimensions (mm)
TARGET_W = 630.0
TARGET_L = 540.0
TARGET_Z_SCALE = 1.6  # 2.5mm plate -> 4.0mm, 0.5mm Braille -> 0.8mm, 5.0mm hinge -> 8.0mm

# Original Lipat Baju.stl board geometry constants
ORIG_Y_MAX = 85.0    # outer edge of Left wing (LENGAN KIRI)
ORIG_Y_MIN = -223.0  # outer edge of Right wing (LENGAN KANAN)
ORIG_X_MAX = 214.0   # collar / Braille edge
ORIG_X_MIN = -78.0   # bottom flap edge
ORIG_Z_MIN = -0.5    # bottom of hinge blocks

SX = TARGET_W / (ORIG_Y_MAX - ORIG_Y_MIN)  # 630 / 308 = 2.0454545...
SY = TARGET_L / (ORIG_X_MAX - ORIG_X_MIN)  # 540 / 292 = 1.8493151...
SZ = TARGET_Z_SCALE

# Hinge cut planes in original STL coordinates
Y_LEFT_GAP = -17.0
Y_RIGHT_GAP = -121.0
X_BOTTOM_GAP = 68.0

# Control box lid-to-base flush assembly offset (exact 1:1 mm)
LID_OFFSET = np.array([-116.0, -1.0, 52.0])

# Control box placement in CAD coordinates (in front of board, centered at X=315)
BOX_ORIG_Y_CENTER = 166.0
BOX_ORIG_X_MAX = 117.69
POD_FRONT_Y_CAD = 580.0

# Colors (0..1)
BLUE = [0.12, 0.38, 0.65]
ORANGE = [0.95, 0.42, 0.07]
DARK_BOX = [0.19, 0.22, 0.26]
LID_SLATE = [0.32, 0.37, 0.43]
BTN_CAP = [0.89, 0.41, 0.09]
BTN_PRIMARY = [0.16, 0.49, 0.72]


def slice_and_cap_rect(mesh: trimesh.Trimesh, plane_normal, plane_origin) -> trimesh.Trimesh:
    """Slice mesh by plane and cap the rectangular hinge cross-section with 2 triangles."""
    sliced = trimesh.intersections.slice_mesh_plane(
        mesh, plane_normal=plane_normal, plane_origin=plane_origin, cap=False
    )
    n = np.asarray(plane_normal, dtype=float)
    n /= np.linalg.norm(n)
    o = np.asarray(plane_origin, dtype=float)
    d = (sliced.vertices - o) @ n
    pts = sliced.vertices[np.abs(d) < 1e-4]
    if len(pts) >= 3:
        axis = int(np.argmax(np.abs(n)))
        other = [i for i in range(3) if i != axis]
        a0, a1 = pts[:, other[0]].min(), pts[:, other[0]].max()
        b0, b1 = pts[:, other[1]].min(), pts[:, other[1]].max()
        corners = []
        for ca, cb in [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]:
            pt = o.copy()
            pt[other[0]] = ca
            pt[other[1]] = cb
            corners.append(pt)
        corners = np.asarray(corners)
        tri_n = np.cross(corners[1] - corners[0], corners[2] - corners[0])
        faces = np.array([[0, 2, 1], [0, 3, 2]]) if np.dot(tri_n, -n) < 0 else np.array([[0, 1, 2], [0, 2, 3]])
        cap = trimesh.Trimesh(vertices=corners, faces=faces, process=False)
        sliced = trimesh.util.concatenate([sliced, cap])
        sliced.merge_vertices(digits_vertex=5)
        sliced.update_faces(sliced.nondegenerate_faces())
        sliced.remove_unreferenced_vertices()
    return sliced


def split_braille(part: trimesh.Trimesh):
    """Separate raised Braille dots along the collar edge for high-contrast rendering."""
    fc = part.triangles_center
    is_braille = (fc[:, 0] > 202.0) & (fc[:, 2] > 2.505)
    b_idx = np.where(is_braille)[0]
    p_idx = np.where(~is_braille)[0]
    p_mesh = part.submesh([p_idx], append=True)
    b_mesh = part.submesh([b_idx], append=True) if len(b_idx) else None
    return p_mesh, b_mesh


def board_to_viewer_cad(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Map folding board to WebGL viewer CAD coordinates (X left->right, Y collar->user, Z up)."""
    v = mesh.vertices
    out_v = np.column_stack([
        (ORIG_Y_MAX - v[:, 1]) * SX,
        (ORIG_X_MAX - v[:, 0]) * SY,
        (v[:, 2] - ORIG_Z_MIN) * SZ,
    ])
    # Determinant is negative (X-flip compensated by viewer presentation mirror), so flip winding.
    out_f = mesh.faces[:, [0, 2, 1]].copy()
    return trimesh.Trimesh(vertices=out_v, faces=out_f, process=False)


def pod_to_viewer_cad(mesh: trimesh.Trimesh, is_lid: bool = False) -> trimesh.Trimesh:
    """Map control pod to WebGL viewer CAD coordinates at exact 1:1 scale."""
    v = mesh.vertices.copy()
    if is_lid:
        v = v + LID_OFFSET
    out_v = np.column_stack([
        315.0 + (BOX_ORIG_Y_CENTER - v[:, 1]),
        POD_FRONT_Y_CAD + (BOX_ORIG_X_MAX - v[:, 0]),
        v[:, 2],
    ])
    out_f = mesh.faces[:, [0, 2, 1]].copy()
    return trimesh.Trimesh(vertices=out_v, faces=out_f, process=False)


def board_to_print_stl(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Map folding board to right-handed 3D-printing space (+X right, +Y back/collar, +Z up)."""
    v = mesh.vertices
    out_v = np.column_stack([
        (ORIG_Y_MAX - v[:, 1]) * SX,
        (v[:, 0] - ORIG_X_MIN) * SY,
        (v[:, 2] - ORIG_Z_MIN) * SZ,
    ])
    out_m = trimesh.Trimesh(vertices=out_v, faces=mesh.faces.copy(), process=False)
    return out_m


def pod_to_print_stl(mesh: trimesh.Trimesh, is_lid: bool = False, assembled_in_scene: bool = False) -> trimesh.Trimesh:
    """Map control pod to right-handed 3D-printing space at exact 1:1 original dimensions."""
    v = mesh.vertices.copy()
    if is_lid and assembled_in_scene:
        v = v + LID_OFFSET
    if assembled_in_scene:
        # Place neatly in front of Y=0 (centered on X=315)
        out_v = np.column_stack([
            315.0 + (BOX_ORIG_Y_CENTER - v[:, 1]),
            -40.0 - (BOX_ORIG_X_MAX - v[:, 0]),
            v[:, 2],
        ])
    else:
        # Pure +90 deg Z rotation, normalized to origin (min X,Y,Z = 0)
        rot_v = np.column_stack([-v[:, 1], v[:, 0], v[:, 2]])
        rot_v -= rot_v.min(axis=0)
        out_v = rot_v
    return trimesh.Trimesh(vertices=out_v, faces=mesh.faces.copy(), process=False)


def make_button_cap(cx: float, cy: float, z_bottom: float = 52.0, height: float = 6.2, radius: float = 9.2) -> trimesh.Trimesh:
    """Create a tactile cylindrical reference pushbutton cap inside a 20 mm lid cutout."""
    cyl = trimesh.creation.cylinder(radius=radius, height=height, sections=32)
    cyl.apply_translation([cx, cy, z_bottom + height / 2.0])
    return cyl


def mesh_to_viewer_dict(name: str, group: str, m: trimesh.Trimesh, color, reference: bool = False):
    return {
        'name': name,
        'group': group,
        'vertices': np.round(m.vertices, 2).tolist(),
        'faces': m.faces.tolist(),
        'color': color,
        'reference': reference,
    }


def compact_revb_model(revb_raw: dict) -> dict:
    """Round Rev B vertices to 0.01 mm and attach pod button hit targets for full compatibility."""
    meshes = []
    for item in revb_raw['meshes']:
        verts = [[round(c, 2) for c in v] for v in item['vertices']]
        m_dict = {
            'name': item['name'],
            'group': item['group'],
            'vertices': verts,
            'faces': item['faces'],
            'color': item['color'],
        }
        if item.get('reference'):
            m_dict['reference'] = True
        # Map Rev B reference button caps & overlays to clickable pod button groups
        if item['name'] in ('button_reference_1', 'button_overlay_back'):
            m_dict['group'] = 'pod_btn_back'
        elif item['name'] in ('button_reference_2', 'button_overlay_next'):
            m_dict['group'] = 'pod_btn_next'
        elif item['name'] in ('button_reference_3', 'button_overlay_repeat'):
            m_dict['group'] = 'pod_btn_reset'
        meshes.append(m_dict)
    return {
        'meshes': meshes,
        'pivots': revb_raw['pivots'],
        'podButtons': [
            {'action': 'back', 'center': [190.0 + 84.0, 595.0 + 45.0, 38.0], 'radius': 13.0},
            {'action': 'next', 'center': [190.0 + 132.0, 595.0 + 45.0, 38.0], 'radius': 13.0},
            {'action': 'reset', 'center': [190.0 + 180.0, 595.0 + 45.0, 38.0], 'radius': 13.0},
        ],
        'meta': {
            'viewTitle': 'Desain awal (Rev B) · papan 630 x 540 mm · satuan milimeter',
            'dimTag': '630 x 540 mm',
        },
    }


def main():
    if not SOURCE_STL.exists() and REPO_SOURCE_STL.exists():
        src_path = REPO_SOURCE_STL
    else:
        src_path = SOURCE_STL
        shutil.copy2(SOURCE_STL, REPO_SOURCE_STL)

    raw = trimesh.load(str(src_path))
    comps = sorted(raw.split(only_watertight=False), key=lambda x: -len(x.faces))
    # Filter out tiny zero-volume stray fragment (e.g. Comp [12] with 2 faces)
    comps = [c for c in comps if len(c.faces) > 4]

    board_raw = comps[0]
    box_body_raw = comps[1]
    lid_plate_raw = comps[2]
    box_tabs_raw = comps[3:7]
    lid_icons_raw = comps[7:12]

    box_full_raw = trimesh.util.concatenate([box_body_raw] + box_tabs_raw)
    lid_icons_full_raw = trimesh.util.concatenate(lid_icons_raw)
    lid_full_raw = trimesh.util.concatenate([lid_plate_raw, lid_icons_full_raw])

    # Split folding board cleanly along the 3 hinge gaps
    left_raw = slice_and_cap_rect(board_raw, [0, 1, 0], [0, Y_LEFT_GAP, 0])
    right_raw = slice_and_cap_rect(board_raw, [0, -1, 0], [0, Y_RIGHT_GAP, 0])
    mid_raw = slice_and_cap_rect(board_raw, [0, -1, 0], [0, Y_LEFT_GAP, 0])
    mid_raw = slice_and_cap_rect(mid_raw, [0, 1, 0], [0, Y_RIGHT_GAP, 0])
    fixed_raw = slice_and_cap_rect(mid_raw, [1, 0, 0], [X_BOTTOM_GAP, 0, 0])
    bottom_raw = slice_and_cap_rect(mid_raw, [-1, 0, 0], [X_BOTTOM_GAP, 0, 0])

    # Export print-ready STLs to both Web Preview/stl_terbaru and output/cad_rev_b/stl_terbaru
    stl_exports = {
        'pelipat_terbaru_utuh_630x540.stl': board_to_print_stl(board_raw),
        'pelipat_terbaru_sayap_kiri.stl': board_to_print_stl(left_raw),
        'pelipat_terbaru_sayap_kanan.stl': board_to_print_stl(right_raw),
        'pelipat_terbaru_tengah_tetap.stl': board_to_print_stl(fixed_raw),
        'pelipat_terbaru_flap_bawah.stl': board_to_print_stl(bottom_raw),
        'pod_kontrol_terbaru_base.stl': pod_to_print_stl(box_full_raw, is_lid=False, assembled_in_scene=False),
        'pod_kontrol_terbaru_lid.stl': pod_to_print_stl(lid_full_raw, is_lid=True, assembled_in_scene=False),
    }
    full_scene_stl = trimesh.util.concatenate([
        stl_exports['pelipat_terbaru_utuh_630x540.stl'],
        pod_to_print_stl(box_full_raw, is_lid=False, assembled_in_scene=True),
        pod_to_print_stl(lid_full_raw, is_lid=True, assembled_in_scene=True),
    ])
    stl_exports['lipat_baju_terbaru_lengkap.stl'] = full_scene_stl

    manifest = []
    for target_root in [WEB_DIR, OUT_DIR]:
        stl_dir = target_root / 'stl_terbaru'
        stl_dir.mkdir(parents=True, exist_ok=True)
        (target_root / 'source').mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, target_root / 'source' / 'Lipat Baju.stl')
        for fname, mesh_obj in stl_exports.items():
            mesh_obj.export(str(stl_dir / fname))

    for fname, mesh_obj in stl_exports.items():
        manifest.append({
            'file': fname,
            'extents_mm': np.round(mesh_obj.extents, 2).tolist(),
            'bounds_min_mm': np.round(mesh_obj.bounds[0], 2).tolist(),
            'bounds_max_mm': np.round(mesh_obj.bounds[1], 2).tolist(),
            'triangles': int(len(mesh_obj.faces)),
        })

    # Build WebGL viewer meshes for Model terbaru
    l_plate, l_braille = split_braille(left_raw)
    r_plate, r_braille = split_braille(right_raw)

    # Exact hinge pivots in WebGL CAD coordinates
    left_pivot_x = round((ORIG_Y_MAX - Y_LEFT_GAP) * SX, 4)    # 208.6364
    right_pivot_x = round((ORIG_Y_MAX - Y_RIGHT_GAP) * SX, 4)  # 421.3636
    bottom_pivot_y = round((ORIG_X_MAX - X_BOTTOM_GAP) * SY, 4) # 270.0000
    hinge_pivot_z = round((4.5 - ORIG_Z_MIN) * SZ, 4)          # 8.0000

    pivots_latest = {
        'left': {'point': [left_pivot_x, 0.0, hinge_pivot_z], 'axis': [0, 1, 0], 'sign': 1},
        'right': {'point': [right_pivot_x, 0.0, hinge_pivot_z], 'axis': [0, 1, 0], 'sign': -1},
        'bottom': {'point': [0.0, bottom_pivot_y, hinge_pivot_z], 'axis': [1, 0, 0], 'sign': 1},
    }

    # Exact 3 button hole centers in WebGL CAD coordinates
    # Original lid holes: x=197.0, y=[194 (back |<), 166 (next >|), 138 (reset square)]
    btn_y_cad = POD_FRONT_Y_CAD + (BOX_ORIG_X_MAX - (197.0 + LID_OFFSET[0]))  # 616.69
    btn_x_back = 315.0 + (BOX_ORIG_Y_CENTER - (194.0 + LID_OFFSET[1]))       # 288.0
    btn_x_next = 315.0 + (BOX_ORIG_Y_CENTER - (166.0 + LID_OFFSET[1]))       # 316.0
    btn_x_reset = 315.0 + (BOX_ORIG_Y_CENTER - (138.0 + LID_OFFSET[1]))      # 344.0

    latest_meshes = [
        mesh_to_viewer_dict('sayap_kiri', 'left', board_to_viewer_cad(l_plate), BLUE),
        mesh_to_viewer_dict('braille_lengan_kiri', 'left', board_to_viewer_cad(l_braille), ORANGE),
        mesh_to_viewer_dict('sayap_kanan', 'right', board_to_viewer_cad(r_plate), BLUE),
        mesh_to_viewer_dict('braille_lengan_kanan', 'right', board_to_viewer_cad(r_braille), ORANGE),
        mesh_to_viewer_dict('panel_tengah_tetap', 'fixed', board_to_viewer_cad(fixed_raw), BLUE),
        mesh_to_viewer_dict('flap_bawah', 'bottom', board_to_viewer_cad(bottom_raw), BLUE),
        mesh_to_viewer_dict('pod_kotak_dasar', 'control', pod_to_viewer_cad(box_full_raw, False), DARK_BOX),
        mesh_to_viewer_dict('pod_tutup', 'control', pod_to_viewer_cad(lid_plate_raw, True), LID_SLATE),
        mesh_to_viewer_dict('pod_simbol_taktil', 'control', pod_to_viewer_cad(lid_icons_full_raw, True), ORANGE),
        mesh_to_viewer_dict('tombol_kembali', 'pod_btn_back', make_button_cap(btn_x_back, btn_y_cad), BTN_CAP, reference=True),
        mesh_to_viewer_dict('tombol_mulai_lanjut', 'pod_btn_next', make_button_cap(btn_x_next, btn_y_cad), BTN_PRIMARY, reference=True),
        mesh_to_viewer_dict('tombol_ulang', 'pod_btn_reset', make_button_cap(btn_x_reset, btn_y_cad), BTN_CAP, reference=True),
    ]

    latest_model = {
        'meshes': latest_meshes,
        'pivots': pivots_latest,
        'podButtons': [
            {'action': 'back', 'center': [round(btn_x_back, 2), round(btn_y_cad, 2), 57.5], 'radius': 10.5},
            {'action': 'next', 'center': [round(btn_x_next, 2), round(btn_y_cad, 2), 57.5], 'radius': 10.5},
            {'action': 'reset', 'center': [round(btn_x_reset, 2), round(btn_y_cad, 2), 57.5], 'radius': 10.5},
        ],
        'meta': {
            'viewTitle': 'Model terbaru · papan 630 x 540 mm · kotak kontrol 1:1',
            'dimTag': '630 x 540 mm',
        },
    }

    # Load existing Rev B preview data so both models are available in the web viewer
    revb_json_path = OUT_DIR / 'source' / 'model_preview_data.json'
    models_dict = {'latest': latest_model}
    if revb_json_path.exists():
        revb_raw = json.loads(revb_json_path.read_text(encoding='utf-8'))
        models_dict['rev_b'] = compact_revb_model(revb_raw)

    bundle = {
        'defaultModel': 'latest',
        'models': models_dict,
    }

    template = (ROOT / 'cad' / 'preview_template.html').read_text(encoding='utf-8')
    payload = json.dumps(bundle, separators=(',', ':'))
    html = template.replace('__MODEL_DATA__', payload)

    (WEB_DIR / 'index.html').write_text(html, encoding='utf-8')
    (OUT_DIR / 'COBA_MEKANISME.html').write_text(html, encoding='utf-8')

    for target_root in [WEB_DIR, OUT_DIR]:
        (target_root / 'source' / 'model_terbaru_preview_data.json').write_text(
            json.dumps(latest_model, separators=(',', ':')), encoding='utf-8'
        )
        (target_root / 'stl_terbaru' / 'manifest_terbaru.json').write_text(
            json.dumps({'board_target_mm': [TARGET_W, TARGET_L, 8.0], 'board_scale': [round(SX, 5), round(SY, 5), SZ], 'control_pod_scale': [1.0, 1.0, 1.0], 'pivots': pivots_latest, 'files': manifest}, indent=2),
            encoding='utf-8',
        )
        cad_copy = target_root / 'source' / 'cad'
        if cad_copy.exists():
            shutil.copy2(ROOT / 'cad' / 'preview_template.html', cad_copy / 'preview_template.html')
            shutil.copy2(ROOT / 'cad' / 'build_latest_model.py', cad_copy / 'build_latest_model.py')

    print(json.dumps({
        'html_bytes': len(html.encode('utf-8')),
        'latest_meshes': len(latest_meshes),
        'latest_triangles': sum(len(m['faces']) for m in latest_meshes),
        'rev_b_included': 'rev_b' in models_dict,
        'stl_files': manifest,
    }, indent=2))


if __name__ == '__main__':
    main()
