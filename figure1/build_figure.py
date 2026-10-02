#!/usr/bin/env python3
"""Extract saved C1 outputs and plot them; never call the native pipeline.

Inputs are immutable copies listed in source_manifest.json. Only closed
InOutBound leaves are decoded; unknown semantics cause an explicit failure.
"""
import argparse
import csv
import hashlib
import json
import platform
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Patch

HERE = Path(__file__).resolve().parent
INPUTS = HERE / 'inputs'
BLUE = '#0072B2'
ORANGE = '#B55400'
INK = '#252A30'


def read(p):
    return json.loads(Path(p).read_text())


def write(p, value):
    Path(p).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def csv_write(path, rows):
    with Path(path).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def world(scene, lane, ds):
    saved = scene['lanes'][str(lane)]
    stations = np.asarray(saved['ds'])
    xyz = np.asarray(saved['center'])
    assert stations.min() <= ds <= stations.max()
    order = np.argsort(stations)
    return [float(np.interp(ds, stations[order], xyz[order, j])) for j in range(3)]


def decode(scene, step):
    rows = []
    for i, shadow in enumerate(step['final']):
        n = shadow['root']
        assert n['type'] == 'InOutBound', 'Unsupported node semantics; do not silently truncate'
        assert n['children'] == [] and all(v is not None for v in shadow['leaf_depth'])
        assert len(shadow['leaf_depth']) == 1
        lo, hi = sorted((float(n['ds_in']), float(n['ds_out'])))
        assert abs(shadow['leaf_depth'][0] - (hi - lo)) < 1e-12
        row = dict(shadow=i, lane=int(n['id']), lo=lo, hi=hi,
                   node_type=n['type'], implicit_tail=False, risk_bound=shadow['risk_bound'])
        assert row == step['segments'][i], 'Independent closed-leaf decoder vs archived segment mismatch'
        rows.append(row)
    groups = defaultdict(list)
    for r in rows:
        groups[r['lane']].append([r['lo'], r['hi']])
    union = []
    for lane, intervals in sorted(groups.items()):
        merged = []
        for lo, hi in sorted(intervals):
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(hi, merged[-1][1])
            else:
                merged.append([lo, hi])
        for lo, hi in merged:
            ds = [lo] + [float(v) for v in scene['lanes'][str(lane)]['ds'] if lo < v < hi] + [hi]
            union.append(dict(lane=lane, ds=[lo, hi], world_polyline=[world(scene, lane, v) for v in sorted(set(ds))]))
    return rows, union


def extract(out):
    checks = []
    def check(name, ok, **details):
        checks.append(dict(name=name, passed=bool(ok), **details))
        assert ok, name
    sm = read(HERE / 'source_manifest.json')
    for r in sm['files']:
        p = HERE / r['bundle_path']
        check('source_sha256:' + r['bundle_path'], sha(p) == r['sha256'] and p.stat().st_size == r['bytes'])
    op = INPUTS / 'native_resolution_control'
    lp = INPUTS / 'native_resolution_local'
    original, local = read(op / 'original.json'), read(lp / 'single_admission.json')
    scene, poses = read(op / 'scene.json'), read(op / 'sensor_poses.json')
    check('scene_identical_bytes', (op / 'scene.json').read_bytes() == (lp / 'scene.json').read_bytes())
    check('poses_identical_bytes', (op / 'sensor_poses.json').read_bytes() == (lp / 'sensor_poses.json').read_bytes())
    check('same_harness', (op / 'source_executed.py').read_bytes() == (lp / 'source_executed.py').read_bytes())
    check('native_resolution', scene['camera']['width'] == 1920 and scene['camera']['height'] == 1080)
    frame_records = []
    with np.load(op / 'depth.npz') as a, np.load(lp / 'depth.npz') as b:
        check('same_frame_keys', a.files == b.files)
        for i, key in enumerate(a.files):
            x, y = a[key], b[key]
            check('depth_array_equal:' + key, np.array_equal(x, y))
            frame_records.append(dict(frame=key, time_s=i / 2, shape=list(x.shape), dtype=str(x.dtype),
                                      array_sha256=hashlib.sha256(x.tobytes(order='C')).hexdigest(),
                                      original_equals_local=True))
    check('steps_before_3p5_equal', original['steps'][:7] == local['steps'][:7])
    check('target_prior_equal', original['steps'][7]['prior'] == local['steps'][7]['prior'])
    check('original_no_grant', original['intervention_applied'] == [])
    check('single_grant_at_3p5', len(local['intervention_applied']) == 1 and local['intervention_applied'][0]['t'] == 3.5)
    grant = local['intervention_applied'][0]
    target = read(INPUTS / 'native_resolution_local_protocol.json')['target']
    check('grant_matches_frozen_target', grant == target)
    target_indices = []
    for run, p, name in [(original, op, 'original'), (local, lp, 'single_admission')]:
        check(name + '_completed', run['status'] == 'completed' and run['error'] is None)
        plain = read(p / (name + '_plain.json'))
        check(name + '_traced_plain_parity', run['steps'] == plain['steps'] and
              run['intervention_applied'] == plain['intervention_applied'] and run['status'] == plain['status'])
        ix = [i for i, e in enumerate(run['events']) if e.get('stage') == 'admission_observed'
              and e.get('t') == 3.5 and e.get('shadow') == target['shadow']]
        check(name + '_unique_target_event', len(ix) == 1)
        target_indices.append(ix[0])
    ia, ib = target_indices
    check('event_prefix_through_target_equal', original['events'][:ia+1] == local['events'][:ib+1],
          original_event_index=ia, local_event_index=ib, equal_events=ia+1)
    check('original_target_would_reject', original['events'][ia]['native_would_reject'])
    check('local_target_next_event_pop', local['events'][ib+1]['stage'] == 'pop' and local['events'][ib+1]['shadow'] == target['shadow'])
    check('no_method_change_beyond_single_grant',
          local['method_source'].replace('if new_shadow_begin not in bwd_searched_begin or grant(new_shadow,t):',
                                         'if new_shadow_begin not in bwd_searched_begin:') == original['method_source'])
    for name, p in [('original', op), ('single_admission', lp)]:
        manifest = read(p / 'start_manifest.json')
        check(name + '_harness_hash', sha(p / 'source_executed.py') == manifest['harness_sha256'])
        for f, h in manifest['native'].items():
            check(name + '_native_source:' + f, sha(INPUTS / 'native_source' / f) == h)
    selections = [('original_3p5', original, 7), ('single_admission_3p5', local, 7), ('original_4p0', original, 8)]
    samples, segments, unions, membership = {}, [], [], []
    for name, run, ix in selections:
        step = run['steps'][ix]
        rows, union = decode(scene, step)
        present = any(r['lane'] == 1 and r['ds'][0] <= 8 <= r['ds'][1] for r in union)
        check(name + '_archived_membership', present == (step['witness_status'] == 'witness_position_present'))
        check(name + '_body_feasible', step['witness']['all_body_hidden'])
        check(name + '_no_implicit_tail', all(not r['implicit_tail'] for r in rows))
        sample = dict(id=name, method=run['method'], time_s=step['t'], camera_xyz=[step['ego_x'], -10, 1.7],
                      output_shadow_count=len(step['final']), full_step=step, union=union,
                      witness_front_xyz=[8, 0, 0], witness_front_in_output=present)
        samples[name] = sample
        write(out / (name + '_full_output.json'), sample)
        for row in rows:
            a, b = world(scene, row['lane'], row['lo']), world(scene, row['lane'], row['hi'])
            segments.append(dict(sample=name, time_s=step['t'], method=run['method'], **row,
                                 x_lo=a[0], y_lo=a[1], x_hi=b[0], y_hi=b[1]))
        for row in union:
            a, b = row['world_polyline'][0], row['world_polyline'][-1]
            unions.append(dict(sample=name, time_s=step['t'], lane=row['lane'], ds_lo=row['ds'][0], ds_hi=row['ds'][1],
                               x_lo=a[0], y_lo=a[1], x_hi=b[0], y_hi=b[1]))
        membership.append(dict(sample=name, time_s=step['t'], method=run['method'], query_lane=1, query_ds=8,
                               world_x=8, world_y=0, front_in_whole_positional_union=present,
                               independent_body_feasible=True, output_shadow_count=len(step['final']),
                               implicit_tails=0, safety_verdict='unmeasured', collision='unmeasured'))
    check('expected_membership_order', [samples[k]['witness_front_in_output'] for k, _, _ in selections] == [False, True, True])
    # Re-evaluate the independent analytic occlusion certificate from geometry;
    # no returned shadow is used as the witness-feasibility reference.
    certs = []
    for i, step in enumerate(original['steps']):
        x = step['ego_x']
        corners = []
        for bx in [8, 11]:
            for by in [-0.5, 0.5]:
                for bz in [0, 1.5]:
                    alpha = 5 / (10 + by)
                    corners.append([x + alpha*(bx-x), 1.7 + alpha*(bz-1.7)])
        a = np.asarray(corners)
        xr, zr = [float(a[:, 0].min()), float(a[:, 0].max())], [float(a[:, 1].min()), float(a[:, 1].max())]
        feasible = -.5 < xr[0] and xr[1] < 5.5 and 0 < zr[0] and zr[1] < 4
        check('independent_body_occlusion:' + str(step['t']), feasible)
        check('analytic_certificate_matches_saved:' + str(step['t']),
              np.allclose(xr, step['witness']['panel_intersection_x'], atol=1e-12, rtol=0) and
              np.allclose(zr, step['witness']['panel_intersection_z'], atol=1e-12, rtol=0))
        certs.append(dict(time_s=step['t'], camera_x=x, panel_intersection_x=xr, panel_intersection_z=zr, all_body_hidden=feasible))
    old_pixel = read(INPUTS / 'historical_analysis/body_sensor_noninterference.json')['results']['native_resolution_control']
    check('historical_pixel_noninterference', len(old_pixel) == 9 and all(r['changed_depth_pixels_with_body'] == 0 for r in old_pixel))
    write(out / 'witness_reference.json', dict(body_xyz_bounds=[[8, 11], [-.5, .5], [0, 1.5]],
          reference_front_lane_ds=[1, 8], reference_front_world_xyz=[8, 0, 0], v=0, a=0,
          interpretation='Independent feasible stationary body; not an object rendered in the original depth images. Membership is for its reference/front position, not a full velocity-history certificate.',
          certificate_basis='Ray intersections with fixed opaque right panel. Fractional-affine coordinate extrema at body corners; affine dependence on camera x covers intermediate times.',
          analytic_rechecks=certs, historical_pixel_audit=old_pixel,
          pixel_audit_reexecuted=False))
    write(out / 'same_prefix_and_intervention.json', dict(
        prefix_times_s=[s['t'] for s in original['steps'][:7]], target_time_s=3.5,
        prefix_steps_sha256=digest(original['steps'][:7]), target_prior_sha256=digest(original['steps'][7]['prior']),
        exact_event_prefix_count=ia+1, exact_event_prefix_sha256=digest(original['events'][:ia+1]),
        target_event_indices_zero_based=target_indices, intervention_applied=local['intervention_applied'],
        target_original_event=original['events'][ia], local_followup_events=local['events'][ib:ib+5],
        original_target_epoch_events=[dict(global_index=i, **e) for i, e in enumerate(original['events']) if e.get('t') == 3.5],
        local_target_epoch_events=[dict(global_index=i, **e) for i, e in enumerate(local['events']) if e.get('t') == 3.5],
        depth_frames=frame_records,
        scope='Same saved scene/poses/depth arrays and exact native execution prefix through the target admission observation. Only that queued candidate is granted once. No new run.'))
    csv_write(out / 'all_output_segments.csv', segments)
    csv_write(out / 'whole_output_union.csv', unions)
    csv_write(out / 'membership.csv', membership)
    write(out / 'scene_coordinates.json', scene)
    write(out / 'audit.json', dict(check_count=len(checks), failed=sum(not c['passed'] for c in checks), checks=checks,
          new_native_runs=0, new_sensor_sequences=0, source_sequences_reused=2,
          selected_snapshots=3, paired_same_time_comparisons=1, independent_scenes=1,
          gpu_used=False, original_source_files_modified=False))
    return scene, samples


def draw_panel(ax, scene, sample, title, recovery=False):
    # The risk road is shown with its saved 1 m width; for lane 999 we show
    # only the saved centerline, not invented normal-offset lane boundaries.
    ax.add_patch(Rectangle((-10, -.5), 30, 1, facecolor='#F0F2F3', edgecolor='#C7CDD2', lw=.7, zorder=0))
    ax.plot([-10, 20], [0, 0], color='#BCC3C9', lw=.6, linestyle=(0, (3, 3)), zorder=1)
    path = np.asarray(scene['lanes']['999']['center'])
    ax.plot(path[:, 0], path[:, 1], color='#B4BBC1', lw=.8, linestyle=(0, (3, 3)), zorder=1)
    cx, cy, _ = sample['camera_xyz']
    # Extreme plan-view witness rays illustrate fixed occlusion geometry.
    for bx, by in [(8, .5), (11, -.5)]:
        ax.plot([cx, bx], [cy, by], color='#ADB4BA', lw=.65, zorder=1)
    for u in sample['union']:
        xy = np.asarray(u['world_polyline'])
        ax.plot(xy[:, 0], xy[:, 1], color=BLUE, lw=6.2, solid_capstyle='butt', zorder=3)
    for panel in scene['panels']:
        ax.plot(panel['x'], [panel['y']]*2, color=INK, lw=3.1, solid_capstyle='butt', zorder=5)
    ax.add_patch(Rectangle((8, -.5), 3, 1, facecolor='none', edgecolor=ORANGE,
                          hatch='////', lw=1.3, linestyle='--', zorder=6))
    ax.plot(8, 0, marker='D', ms=4.3, markerfacecolor='white', markeredgecolor=ORANGE,
            markeredgewidth=1.3, linestyle='none', zorder=7)
    ax.annotate('w = (8, 0)', xy=(8, .1), xytext=(8, 1.8), fontsize=8.5,
                ha='center', va='center', color=ORANGE,
                arrowprops=dict(arrowstyle='-', lw=.75, color=ORANGE), zorder=8)
    ax.plot(cx, cy, 'o', color=INK, ms=4, zorder=6)
    ax.plot([-4, cx], [-10, -10], color=INK, lw=1.4, zorder=4)
    ax.annotate('Camera', xy=(cx, cy), xytext=(-4, -8.35), fontsize=8.5, color=INK,
                arrowprops=dict(arrowstyle='-', color=INK, lw=.65), ha='left')
    ax.text(6.2, -5.05, 'Opaque panels', fontsize=8.5, color=INK, va='center')
    ax.annotate('Other returned\noutput', xy=(0, -4.4), xytext=(-4.1, -2.5), fontsize=8,
                color=BLUE, va='center', arrowprops=dict(arrowstyle='-', color=BLUE, lw=.65))
    present = sample['witness_front_in_output']
    label = ('Witness position present again' if recovery else 'Witness position retained') if present else 'Witness position omitted'
    ax.set_title(title, loc='left', fontsize=10, fontweight='bold', pad=23)
    ax.text(0, 1.025, label, transform=ax.transAxes, fontsize=9, color=BLUE if present else ORANGE)
    ax.set_xlim(-4.8, 15.2)
    ax.set_ylim(-11.2, 2.8)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xticks([-4, 0, 4, 8, 12])
    ax.set_yticks([-10, -5, 0])
    ax.tick_params(labelsize=8, length=3, width=.6, pad=2)
    ax.set_xlabel('World x (m)', fontsize=9, labelpad=3)
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color('#A1A9B0')
        ax.spines[spine].set_linewidth(.6)
    # Assert that every returned positional interval is completely in view.
    for u in sample['union']:
        for x, y, z in u['world_polyline']:
            assert -4.8 <= x <= 15.2 and -11.2 <= y <= 2.8


def figures(out, scene, samples):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                         'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'hatch.linewidth': .6, 'axes.unicode_minus': True})
    handles = [Line2D([0], [0], color=BLUE, lw=5.5, solid_capstyle='butt', label='Whole-output union (position only)'),
               Patch(facecolor='none', edgecolor=ORANGE, hatch='////', linestyle='--', label='Feasible witness body; diamond = w')]
    def save(fig, stem):
        # No bbox_inches='tight': keep physical insertion size and point sizes fixed.
        for suffix in ['pdf', 'svg', 'png']:
            fig.savefig(out / (stem + '.' + suffix), dpi=300, facecolor='white')
        plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(7.15, 3.55))
    fig.subplots_adjust(left=.065, right=.993, bottom=.275, top=.855, wspace=.15)
    draw_panel(axs[0], scene, samples['original_3p5'], '(a) Original  |  t = 3.5 s')
    draw_panel(axs[1], scene, samples['single_admission_3p5'], '(b) Single admission  |  t = 3.5 s')
    axs[0].set_ylabel('World y (m)', fontsize=9, labelpad=2)
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.515, .12), ncol=2,
               frameon=False, fontsize=8.2, handlelength=2.2, columnspacing=1.6)
    fig.text(.515, .078, 'Same scene, 1920 × 1080 depth history, and execution prefix; one admission at t = 3.5 s.',
             ha='center', va='center', fontsize=8)
    fig.text(.515, .032, 'Top view · All returned outputs shown · No safety verdict or collision measurement',
             ha='center', va='center', fontsize=8, color='#565E65')
    save(fig, 'c1_1920_t3p5_original_vs_single_admission')
    fig, ax = plt.subplots(figsize=(3.5, 3.6))
    fig.subplots_adjust(left=.132, right=.985, bottom=.325, top=.85)
    draw_panel(ax, scene, samples['original_4p0'], 'Original  |  t = 4.0 s', recovery=True)
    ax.set_ylabel('World y (m)', fontsize=9, labelpad=2)
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.54, .13), ncol=1,
               frameon=False, fontsize=8, handlelength=2.2)
    fig.text(.54, .082, 'Next observation epoch; no admission intervention.', ha='center', fontsize=8)
    fig.text(.54, .035, 'Later regeneration does not erase the t = 3.5 s omission.', ha='center', fontsize=7.7, color='#565E65')
    save(fig, 'c1_1920_t4p0_original')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=HERE / 'generated')
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    scene, samples = extract(out)
    figures(out, scene, samples)
    write(out / 'extraction_manifest.json', dict(
        created_utc=datetime.now(timezone.utc).isoformat(), command=['python','figure1/build_figure.py','--out','<OUTPUT>'],
        python=sys.version, executable=Path(sys.executable).name,
        platform=platform.platform(), numpy=np.__version__, matplotlib=matplotlib.__version__,
        source_manifest_sha256=sha(HERE / 'source_manifest.json'), figure_script_sha256=sha(__file__),
        native_runs=0, device='CPU', source_inputs_modified=False,
        historical_settings=['../inputs/native_resolution_control/start_manifest.json',
                             '../inputs/native_resolution_local/start_manifest.json',
                             '../inputs/native_resolution_protocol.json', '../inputs/native_resolution_local_protocol.json'],
        image_settings=dict(main_width_in=7.15, main_height_in=3.55, main_width_mm=181.61,
                            secondary_width_in=3.5, secondary_height_in=3.6, png_dpi=300,
                            minimum_main_font_pt=8, minimum_secondary_font_pt=7.7,
                            svg_text_editable=True, pdf_fonttype=42,
                            output_stroke_width_pt=6.2, output_stroke_is_not_physical_lateral_extent=True),
        display_limits=dict(world_x=[-4.8, 15.2], world_y=[-11.2, 2.8], equal_aspect=True,
                            road_context_cropped=True, all_returned_output_fully_visible=True),
        scope='Offline extraction from two existing saved sequences in one synthetic scene. Three snapshots; one same-time paired comparison. No new experiment or independent scene.'))
    print(json.dumps(dict(output=str(out), audit=read(out / 'audit.json')['check_count'], failed=0)))


if __name__ == '__main__':
    main()
