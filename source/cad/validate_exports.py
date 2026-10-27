"""Independent validation of Rev B exports; does not rebuild the CAD model.

Run with bundled Python 3.12. STL checks run in system Python/trimesh;
3MF checks use lib3mf; STEP import uses CadQuery/OCP.
"""
from pathlib import Path
import sys
import json
import subprocess
import math

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'cad_rev_b'
REPORT_PATH = OUT / 'independent_validation.json'


def stl_worker():
    import trimesh
    import numpy as np
    result = {}
    files = sorted((OUT / 'stl').glob('*.stl')) + sorted((OUT / 'tests').glob('*.stl'))
    for path in files:
        try:
            m = trimesh.load_mesh(path, file_type='stl', process=True)
            connected = len(m.split(only_watertight=False))
            extents = m.extents
            checks = {
                'watertight': bool(m.is_watertight),
                'winding_consistent': bool(m.is_winding_consistent),
                'positive_volume': bool(m.volume > 0),
                'single_connected_body': connected == 1,
                'fits_260_cube': bool(np.all(extents <= 260.0 + 1e-4)),
                'on_or_above_z0': bool(m.bounds[0, 2] >= -1e-4),
            }
            result[path.stem] = {
                'path': str(path.relative_to(ROOT)),
                'checks': checks,
                'passed': all(checks.values()),
                'connected_bodies': connected,
                'bounds_mm': m.bounds.tolist(),
                'extents_mm': extents.tolist(),
                'volume_mm3': float(m.volume),
                'vertices': len(m.vertices),
                'triangles': len(m.faces),
            }
        except Exception as e:
            result[path.stem] = {'path': str(path), 'passed': False, 'error': repr(e)}
    print(json.dumps({'trimesh_version': trimesh.__version__, 'parts': result}))


if '--stl-worker' in sys.argv:
    stl_worker()
    raise SystemExit(0)

sys.path.insert(0, str(ROOT / '.cad_runtime'))
import numpy as np
import trimesh
import lib3mf
import cadquery as cq


def collect_iterator(iterator):
    items = []
    while iterator.MoveNext():
        items.append(iterator.GetCurrentMeshObject() if hasattr(iterator, 'GetCurrentMeshObject') else iterator.GetCurrent())
    return items


def main():
    manifest_path = OUT / 'parts_manifest.json'
    if not manifest_path.exists():
        raise SystemExit('Model build has not reached parts_manifest.json; run this after exports finish.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    command = [r'C:\Python313\python.exe', str(Path(__file__)), '--stl-worker']
    worker = subprocess.run(command, capture_output=True, text=True, check=True, timeout=240)
    stl = json.loads(worker.stdout)
    wrapper = lib3mf.get_wrapper()
    three_mf = {}
    for path in sorted((OUT / '3mf').glob('*.3mf')):
        row = {'path': str(path.relative_to(ROOT))}
        try:
            model = wrapper.CreateModel()
            reader = model.QueryReader('3mf')
            reader.ReadFromFile(str(path))
            warnings = [reader.GetWarning(i) for i in range(reader.GetWarningCount())]
            meshes = collect_iterator(model.GetMeshObjects())
            items = collect_iterator(model.GetBuildItems())
            mesh_checks = []
            mesh_values = []
            for mesh in meshes:
                vertices = np.asarray([list(v.Coordinates) for v in mesh.GetVertices()], dtype=float)
                faces = np.asarray([list(t.Indices) for t in mesh.GetTriangleIndices()], dtype=int)
                m = trimesh.Trimesh(vertices, faces, process=False)
                mesh_checks.append({'valid': bool(mesh.IsValid()), 'manifold_and_oriented': bool(mesh.IsManifoldAndOriented())})
                mesh_values.append((vertices, m))
            same = stl['parts'].get(path.stem)
            reference_present = same is not None
            bounds_match = volume_match = on_bed = False
            actual_bounds = None
            volume = None
            if len(mesh_values) == 1 and len(items) == 1:
                vertices, m = mesh_values[0]
                fields = np.asarray([list(row) for row in items[0].GetObjectTransform().Fields], dtype=float)
                transformed = vertices @ fields[:3] + fields[3]
                actual_bounds = [transformed.min(axis=0).tolist(), transformed.max(axis=0).tolist()]
                transformed_extents = np.ptp(transformed, axis=0)
                volume = float(m.volume)
                on_bed = bool(np.all(transformed.min(axis=0) >= -1e-3) and np.all(transformed.max(axis=0) <= 260.0 + 1e-3))
                if same:
                    bounds_match = bool(np.allclose(transformed_extents, same['extents_mm'], atol=2e-3, rtol=1e-6))
                    volume_match = bool(math.isclose(volume, same['volume_mm3'], rel_tol=1e-4, abs_tol=1e-2))
            checks = {
                'reader_zero_warnings': len(warnings) == 0,
                'unit_millimeter': model.GetUnit() == lib3mf.ModelUnit.MilliMeter,
                'single_mesh_object': len(meshes) == 1,
                'single_build_item': len(items) == 1,
                'all_meshes_valid': all(x['valid'] for x in mesh_checks),
                'all_meshes_manifold_oriented': all(x['manifold_and_oriented'] for x in mesh_checks),
                'matching_stl_exists': reference_present,
                'extents_match_stl': bounds_match,
                'volume_matches_stl': volume_match,
                'build_item_inside_260_cube': on_bed,
            }
            row.update({'checks': checks, 'passed': all(checks.values()), 'reader_warnings': warnings, 'meshes': mesh_checks, 'build_bounds_mm': actual_bounds, 'volume_mm3': volume})
        except Exception as e:
            row.update({'passed': False, 'error': repr(e)})
        three_mf[path.stem] = row

    step_result = {}
    step_path = OUT / 'step' / 'assembly_open.step'
    try:
        shape = cq.importers.importStep(str(step_path)).val()
        solids = shape.Solids()
        expected_instances = sum(x['quantity'] for x in manifest if x['category'] == 'print')
        # Assembly additionally includes six metal pin references, three visual
        # button envelopes, and one visual volume knob, as documented in source.
        expected_total_solids = expected_instances + 6 + 3 + 1
        valid = shape.isValid()
        positive = all(s.Volume() > 0 for s in solids)
        checks = {
            'brep_valid': bool(valid),
            'all_solids_positive_volume': positive,
            'solid_count_matches_assembly': len(solids) == expected_total_solids,
        }
        step_result = {'path': str(step_path.relative_to(ROOT)), 'checks': checks, 'passed': all(checks.values()), 'solid_count': len(solids), 'expected_solid_count': expected_total_solids, 'total_volume_mm3': sum(s.Volume() for s in solids)}
    except Exception as e:
        step_result = {'passed': False, 'error': repr(e)}

    step_parts = {}
    for part in manifest:
        path = OUT / 'step' / (part['part'] + '.step')
        row = {'path': str(path.relative_to(ROOT))}
        try:
            shape = cq.importers.importStep(str(path)).val()
            solids = shape.Solids()
            volume = sum(s.Volume() for s in solids)
            checks = {
                'brep_valid': bool(shape.isValid()),
                'single_solid': len(solids) == 1,
                'positive_volume': bool(volume > 0),
                'volume_matches_manifest_brep': math.isclose(volume, part['volume_mm3'], rel_tol=1e-7, abs_tol=1e-2),
            }
            row.update({'checks': checks, 'passed': all(checks.values()), 'solid_count': len(solids), 'volume_mm3': volume})
        except Exception as e:
            row.update({'passed': False, 'error': repr(e)})
        step_parts[part['part']] = row

    manifest_names = {x['part'] for x in manifest}
    stl_names = set(stl['parts'])
    three_mf_names = set(three_mf)
    coverage = {'manifest_parts': len(manifest_names), 'stl_parts': len(stl_names), '3mf_parts': len(three_mf_names), 'stl_missing': sorted(manifest_names - stl_names), '3mf_missing': sorted(manifest_names - three_mf_names), 'unexpected_stl': sorted(stl_names-manifest_names), 'unexpected_3mf': sorted(three_mf_names-manifest_names)}
    coverage['passed'] = manifest_names == stl_names == three_mf_names
    failures = {
        'stl': [n for n,r in stl['parts'].items() if not r['passed']],
        '3mf': [n for n,r in three_mf.items() if not r['passed']],
        'step': [] if step_result['passed'] else ['assembly_open.step'],
        'step_parts': [n for n,r in step_parts.items() if not r['passed']],
        'coverage': [] if coverage['passed'] else ['manifest/export names mismatch'],
    }
    report = {'scope': 'Independent exported-file checks; no physical print or strength test; no motion collision validation in this script.', 'passed': not any(failures.values()), 'failures': failures, 'coverage': coverage, 'stl_runtime': stl['trimesh_version'], 'stl': stl['parts'], '3mf': three_mf, 'step_assembly': step_result, 'step_parts': step_parts}
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'failures': failures, 'coverage': coverage, 'report': str(REPORT_PATH), 'step': step_result}, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
