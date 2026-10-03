#!/usr/bin/env python3
"""V3 label-scope correction; standard-library-only. No native imports or pickle load.

Checks anonymized public archived bytes, independent finite reference/body feasibility,
finite tree position projection, old query accounting, and historical cohorts.
The public archive has redacted personal paths/links and refreshed source hashes.
No scientific measurements, predicates, or expected results were changed.
"""
import argparse, collections, csv, datetime, fractions, hashlib, itertools, json
import math, pathlib, platform, zipfile

HERE=pathlib.Path(__file__).resolve().parent
OLD='runs/semantic_small_graph_v2/'
SENSOR='send/SPAIS_C1_native_sensor_validation/c1/'
NATIVE='send/SPAIS_C1_native_sensor_validation/d1/'
BOUND='send/SPAIS_reaudit/boundaries/'
F=fractions.Fraction

def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def write_rows(p,rows):
    with p.open('w') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')

def position(forest,lane,ds,lengths,ignore_forward=False):
    """Position overapproximation only. Unresolved if any applicable tail remains.

    Finite terminal InBound is bounded by lane endpoint in backward trees.
    Positive IDs decrease ds in traffic direction in this corpus.
    """
    intervals=[];unknown=[]
    def walk(n,index):
        lid=n['id'];typ=n['type'];children=n.get('children') or []
        if lid not in lengths:unknown.append([index,'unknown_lane',lid]);return
        if typ=='InOutBound':lo,hi=n.get('ds_out'),n.get('ds_in')
        elif typ=='InBound':lo,hi=0,n.get('ds_in')
        elif typ=='OutBound':lo,hi=n.get('ds_out'),lengths[lid]
        elif typ=='ShadowNode':lo,hi=0,lengths[lid]
        else:unknown.append([index,'unknown_type',typ]);return
        if lo is None or hi is None:unknown.append([index,'missing_bound'])
        elif lid==lane:intervals.append([min(lo,hi),max(lo,hi)])
        if not children and typ not in ['InBound','InOutBound']:
            unknown.append([index,'unbounded_terminal',typ])
        for c in children:walk(c,index)
    for i,s in enumerate(forest):
        if ignore_forward and s['risk_bound']:continue
        if any(d is None for d in s.get('leaf_depth',[])):unknown.append([i,'truncated_leaf_depth'])
        walk(s['root'],i)
    present=any(a<=ds<=b for a,b in intervals)
    return dict(status='present' if present else 'unresolved' if unknown else 'absent',
                position_present=present,absence_supported=not unknown,unknown=unknown,intervals=intervals)

def visible_hit(q,intervals,length=F(3)):
    return any(max(q-length,F(a))<=min(q,F(b)) for a,b in intervals)

def transition(q,v,a,dt=F(1,2)):
    a=F(a);terminal=v+a*dt
    if 0<=terminal<=15:return q+v*dt+a*dt*dt/2,terminal
    bound=F(0 if terminal<0 else 15);hit=(bound-v)/a
    return q+v*hit+a*hit*hit/2+bound*(dt-hit),bound

def reference_layers(fields):
    times=sorted(map(F,fields));current={(F(q,4),F(v)) for q in range(-48,-15) for v in range(16)
        if not visible_hit(F(q,4),fields[str(float(times[0]))])}
    result=[current]
    for t in times[1:]:
        obs=fields[str(float(t))];nxt=set()
        for q,v in current:
            for a in [-8,-4,0,4]:
                q1,v1=transition(q,v,a)
                if q1-3>=-20 and q1<=10 and not visible_hit(q1,obs):nxt.add((q1,v1))
        result.append(nxt);current=nxt
    return result

def body_hidden(x,gap):
    points=[]
    for bx,by,bz in itertools.product([8.,11.],[-.5,.5],[0.,1.5]):
        a=5/(10+by);points.append([x+a*(bx-x),1.7+a*(bz-1.7)])
    bounds=[min(p[0] for p in points),max(p[0] for p in points),
            min(p[1] for p in points),max(p[1] for p in points)]
    margin=min(bounds[0]-gap,5.5-bounds[1],bounds[2],4-bounds[3])
    return dict(feasible=margin>0,bounds=bounds,strict_margin=margin,
                scope='stationary 3x1x1.5 m body occlusion under fixed ideal panel geometry; linear camera segments bounded by endpoints')

def signature(s):
    leaves=[]
    def walk(n):
        if n.get('children'):
            for c in n['children']:walk(c)
        else:leaves.append(n['id'])
    walk(s['root'])
    return set(zip(leaves,s['leaf_depth']))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact',type=pathlib.Path,default=HERE)
    ap.add_argument('--output',type=pathlib.Path,required=True);args=ap.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((args.artifact/'manifest.json').read_text())
    expected=json.loads((args.artifact/'expected.json').read_text())
    z=zipfile.ZipFile(args.artifact/'evidence.zip');checks=[];outputs=[];events=[];queries=[];witnesses=[];heuristics=[]
    def read(name):return json.loads(z.read(name))
    def check(name,actual,wanted=True,scope=''):
        checks.append(dict(name=name,actual=actual,expected=wanted,pass_=actual==wanted,scope=scope))
    def event_rows(group,case,method,source,raw,filter_t=None):
        for i,e in enumerate(raw):
            t=e.get('t',e.get('time'))
            if filter_t is None or t in filter_t:
                events.append(dict(schema='spais.e3.event.v1',group=group,case=case,method=method,
                    source=source,source_event_ordinal=i,event=e))
    def output_row(group,case,method,source,index,t,forest,lengths,witness_lanes,feasibility,next_t=None,prior=None,consumer='none',ignore_forward=False):
        uid='%s/%s/%s/%s'%(group,case,method,index)
        memberships={str(l):position(forest,l,8,lengths,ignore_forward) for l in witness_lanes}
        row=dict(schema='spais.e3.output.v1',output_id=uid,group=group,case=case,method=method,
          source=source,source_update_index=index,t_sense=t,t_return_model=t,t_return_wall='not_recorded',
          next_observation_time=next_t,consumer_query_id=consumer,
          consumption_scope='No live caller consumption is inferred; legacy checker is a separately transplanted fixed query fixture.',
          returned_forest=forest,returned_output_sha256=sha(canon(forest)),prior_forest=prior,
          input_contract='valid_within_declared_synthetic_schema',
          feasibility=feasibility,whole_output_membership=memberships,
          semantic_scope='position projection only; presence does not certify speed/history',
          empty_output_flag=not forest)
        outputs.append(row);return row
    check('archive_sha256',sha((args.artifact/'evidence.zip').read_bytes()),manifest['archive_sha256'])
    mismatches=[]
    for entry in manifest['files']:
        data=z.read(entry['path'])
        if sha(data)!=entry['sha256'] or len(data)!=entry['bytes']:mismatches.append(entry['path'])
    check('archived_file_hash_mismatches',mismatches,[])
    lineage=[]
    def source_match(role,path,wanted):
        actual=sha(z.read(path)) if path in z.namelist() else None
        lineage.append(dict(role=role,archived_path=path,actual_sha256=actual,recorded_sha256=wanted,
                            status='matched' if actual==wanted else 'unavailable' if actual is None else 'mismatch'))
        check('source_lineage/'+role,actual,wanted)
    old_manifest=read(OLD+'manifest.json')
    for path,h in old_manifest['source'].items():source_match('old/'+path,OLD+pathlib.Path(path).name,h)
    source_match('old/input',OLD+'inputs.json',old_manifest['inputs_sha256'])
    for path,h in old_manifest['generated_interventions'].items():source_match('old/generated/'+path,OLD+path,h)
    for folder in ['runs/semantic_minimal_trace_v2/','runs/semantic_manuscript_audit_v1/',
                   'runs/semantic_action_check_serialization_v3/','runs/semantic_action_far_control_v2/']:
        m=read(folder+'manifest.json');h=m.get('source_sha256',next(iter(m.get('source',{}).values()),None))
        source_match(folder+'executed',folder+'source_executed.py',h)
    control_manifest=read('runs/semantic_controls_v1/manifest.json')
    for name,h in control_manifest['source'].items():source_match('control/'+name,'runs/semantic_controls_v1/'+name,h)
    for batch in ['development_v1','confirmation_v3','native_resolution_control','native_resolution_local']:
        m=read(SENSOR+batch+'/start_manifest.json')
        source_match('sensor/'+batch,SENSOR+batch+'/source_executed.py',m['harness_sha256'])
        for name,h in m['native'].items():source_match('sensor/'+batch+'/'+name,'repos/rss_occlusion/risk_analysis/'+name,h)
    dproto=read(NATIVE+'development_protocol.json')
    for path,h in dproto['frozen_source_sha256'].items():
        stored=path if path in z.namelist() else OLD+pathlib.Path(path).name
        source_match('native_D1/'+path,stored,h)
    # External binary inputs are only hash-verified at collection time. The
    # standalone validator does not have them and does not deserialize pickle.
    external={x['path']:x for x in manifest['external_native_replay_inputs']}
    for folder in ['runs/semantic_action_check_serialization_v3/','runs/semantic_action_far_control_v2/']:
        for path,h in read(folder+'manifest.json')['inputs'].items():
            check('collected_external_hash/'+folder+path,external[path]['sha256'],h,
                  'Collection-time bytes matched; replay context not bundled or executed.')
    # Original model and preservation controls.
    old=read(OLD+'pipeline_two_lanes__original.json');fields=old['reference']['fields']
    layers=reference_layers(fields)
    check('old_independent_finite_reference_counts',[len(x) for x in layers],expected['old_c1_reference_counts'])
    stationary_feasible=all(not visible_hit(F(-8),v) for v in fields.values())
    check('old_stationary_witness_observation_feasible',stationary_feasible)
    witnesses.append(dict(id='old_stationary',group='R-old-C1',q=-8,front_ds=8,footprint_q=[-11,-8],
        v=0,a=0,feasibility='feasible' if stationary_feasible else 'infeasible',
        evidence=OLD+'witness.json',observation_operator='closed visible nearest-waypoint cells at 0.5 s epochs',
        semantics='position witness; not a goal-completion oracle'))
    old_records={}
    for method in ['original','single_admission','mature_coverage_guard','structural_key']:
        src=OLD+'pipeline_two_lanes__'+method+'.json';raw=read(src);old_records[method]=raw
        absent=[]
        for i,s in enumerate(raw['steps']):
            row=output_row('R-old-C1','pipeline_two_lanes',method,src,i,s['t'],s['shadows'],{1:20,2:10},[1],
                {'status':'feasible','witness_id':'old_stationary'},s['t']+.5 if i<8 else None,
                consumer='legacy_near_and_far_query_fixture' if i==8 else 'none')
            if row['whole_output_membership']['1']['status']=='absent':absent.append(s['t'])
            missing=0
            for q,v in layers[i]:
                lane,ds=(1,-q) if q<=0 else (2,10-q)
                if position(s['shadows'],lane,ds,{1:20,2:10})['status']=='absent':missing+=1
            check('finite_position_missing/%s/%s'%(method,s['t']),missing,s['missing_count'])
        check('old_absence/'+method,absent,expected['old_c1_original_absent_times'] if method=='original' else [])
    event_rows('R-old-C1','pipeline_two_lanes','original','runs/semantic_minimal_trace_v2/events.json',
        read('runs/semantic_minimal_trace_v2/events.json'),[3.])
    trace=read('runs/semantic_minimal_trace_v2/steps.json')
    check('old_logged_plain_output_parity',[s['final'] for s in trace],[s['shadows'] for s in old['steps']])
    for case,src,key in [('normal_duplicate','runs/semantic_controls_v1/normal_duplicate__original.json','normal_duplicate_absent_times'),
      ('redundant_equal_copy',OLD+'redundant_equal_copy__original.json','redundant_equal_copy_absent_times')]:
        raw=read(src);absent=[];obs=raw.get('fields',raw.get('reference',{}).get('fields'))
        for i,s in enumerate(raw['steps']):
            feasible=not visible_hit(F(-8),obs[str(s['t'])])
            row=output_row('R-C1-controls',case,'original',src,i,s['t'],s['shadows'],{1:20,2:10},[1],
                {'status':'feasible' if feasible else 'infeasible','witness_id':'old_stationary'},s['t']+.5 if i<8 else None)
            if row['whole_output_membership']['1']['status']=='absent':absent.append(s['t'])
        check('preservation_control/'+case,absent,expected[key])
    # Synthetic sensor schemas. Reuse existing tracer/plain observations; no rerun.
    sensor_records={};sensor_cohort=collections.Counter()
    for group in ['development_v1','confirmation_v3','native_resolution_control','native_resolution_local']:
        for summary in read(SENSOR+group+'/summary.json'):
            directory=SENSOR+group+'/'+summary['case']+'/';method=summary['method']
            raw=read(directory+method+'.json');plain=read(directory+method+'_plain.json')
            sensor_cohort['traced_sequences']+=1;sensor_cohort['plain_sequences']+=1
            sensor_cohort['native_updates']+=len(raw['steps'])+len(plain['steps'])
            check('sensor_saved_parity/'+group+'/'+summary['case']+'/'+method,
                [raw[k] for k in ['steps','status','intervention_applied']],[plain[k] for k in ['steps','status','intervention_applied']])
            if summary['case']!='v0.5_g-0.5' or group=='development_v1':continue
            sensor_records[(group,method)]=raw;scene=read(directory+'scene.json')
            lengths={int(k):max(v['ds']) for k,v in scene['lanes'].items()};resolution=scene['camera']['width']
            for i,s in enumerate(raw['steps']):
                cert=body_hidden(s['ego_x'],raw['config']['gap'])
                check('body_certificate/%s/%s/%s'%(group,method,s['t']),cert['feasible'],s['witness']['all_body_hidden'])
                output_row('R-sensor'+str(resolution),summary['case'],method,directory+method+'.json',i,s['t'],s['final'],lengths,[1],
                    {'status':'feasible' if cert['feasible'] else 'unresolved','certificate':cert},s['t']+.5 if i<8 else None,s['prior'])
            event_rows('R-sensor'+str(resolution),summary['case'],method,directory+method+'.json',raw['events'],[2. if resolution==640 else 3.5])
    sensor_cohort['native_sequences']=sensor_cohort['traced_sequences']+sensor_cohort['plain_sequences']
    sensor_cohort['pre_native_instrumentation_failure']=1
    check('sensor_cohort_denominator',dict(sensor_cohort),expected['sensor_existing_execution_denominator'])
    for group,res,targett in [('confirmation_v3',640,2.),('native_resolution_control',1920,3.5)]:
        original=sensor_records[(group,'original')]
        single=sensor_records[('confirmation_v3' if res==640 else 'native_resolution_local','single_admission')]
        check('sensor%d_original_absent'%res,[s['t'] for s in original['steps'] if s['witness_status']=='witnessed_omission'],expected['sensor%d_original_absent_times'%res])
        check('sensor%d_single_absent'%res,[s['t'] for s in single['steps'] if s['witness_status']=='witnessed_omission'],expected['sensor%d_single_absent_times'%res])
        check('sensor%d_single_applied_once'%res,len(single['intervention_applied']),1)
        check('sensor%d_same_prefix'%res,[s for s in single['steps'] if s['t']<targett],[s for s in original['steps'] if s['t']<targett])
        check('sensor%d_same_target_prior'%res,next(s['prior'] for s in single['steps'] if s['t']==targett),next(s['prior'] for s in original['steps'] if s['t']==targett))
        st=next(s for s in original['steps'] if s['t']==targett)
        if res==640:
            heuristics.append(dict(rule='empty_output',case='R-sensor640/t2',rule_conclusion='no_flag' if st['final'] else 'flag',
                independent_result='feasible designated position absent',failure_mode='false_reassurance',evidence=group+'/v0.5_g-0.5/original.json#steps/4',output_count=len(st['final'])))
        else:
            mature=[e['mature'] for e in original['events'] if e.get('t')==targett and e['stage']=='primitive_return' and e['input']['root'].get('ds_in')==1.5 and e['input']['root'].get('ds_out')==1]
            retained=bool(mature and mature[0] in st['final'])
            check('1920_short_mature_retained',retained)
            heuristics.append(dict(rule='representative_exists',case='R-sensor1920/t3.5',rule_conclusion='preserved' if retained else 'no_reassurance',
                independent_result='ds8 absent despite short [1,1.5] retained',failure_mode='false_reassurance',evidence=group+'/v0.5_g-0.5/original.json',retained=retained))
            final=position(original['steps'][-1]['final'],1,8,{1:20,2:10,999:40})['status']
            heuristics.append(dict(rule='final_only',case='R-sensor1920/t4',rule_conclusion=final,
                independent_result='t3.5 absent; t4 present',failure_mode='misses_intermediate_omission',evidence=group+'/v0.5_g-0.5/original.json'))
    witnesses.append(dict(id='sensor_stationary',groups=['R-sensor640','R-sensor1920'],front_ds=8,
        body_world={'x':[8,11],'y':[-.5,.5],'z':[0,1.5]},v=0,a=0,
        feasibility='strict panel occlusion bounds over selected 0.5 m/s camera path; no model mask equivalence transferred',
        continuous_segment_argument='Plane intersection is affine in camera x and coordinatewise fractional-affine with positive denominator on the box; endpoint extrema bound each linear camera segment.'))
    # Original checker fixture: count stored queries; do not execute checker.
    for near,src in [(True,'runs/semantic_action_check_serialization_v3/results.json'),(False,'runs/semantic_action_far_control_v2/results.json')]:
        raw=read(src);baseline=raw['original']['checks']
        for method,data in raw.items():
            checks_for_arm=data['checks'];allowed=[]
            check('legacy_query_input_parity/%s/%s'%(near,method),[x['input'] for x in checks_for_arm],[x['input'] for x in baseline])
            for i,c in enumerate(checks_for_arm):
                allow=bool(c['result'][0]);allowed.append(i) if allow else None
                queries.append(dict(schema='spais.e3.query.v1',id='legacy_%s/%s/%d'%('near' if near else 'far',method,i),
                    source=src,method=method,query_index=i,query=c['input'],native_result=c['result'],native_verdict='allow' if allow else 'reject',
                    fixture='D05 context with model-level C1 component transplant; not sensor640/1920',
                    consumed_output_relation='legacy transformed model component; detailed native metrics retained in raw archive',
                    actual_live_planner_execution=False,independent_hazard_evidence='not_recomputed_in_E3',collision='not_measured'))
            check('legacy_allowed/%s/%s'%(near,method),len(allowed),expected['old_checker_near_allowed'][method] if near else 18)
            if near and method!='original':check('legacy_repaired_ids/'+method,allowed,expected['old_checker_repaired_allowed_ids'])
    # Constructed boundary and alternate-owner scope.
    boundary_specs=[('D1_subset_fork','development','original'),('D1_subset_fork','mature_only_ablation','mature_only_off'),
                    ('V3_alternate_owner','validation','original'),('V5_implicit_truncation','validation','original')]
    for case,subdir,method in boundary_specs:
        src=BOUND+subdir+'/'+case+'__'+method+'.json';raw=read(src);trunk=30 if case.startswith('V5') else 0
        lens={1:20,2:20,3:20,4:20,5:trunk};row=output_row('B-D1',case,method,src,0,0,raw['final_forest'],lens,[2,3],
            {'status':'feasible','basis':'stationary body ds[8,11], nearest visible boundary14.75; constructed initial branches'},None,raw['initial_forest'])
        statuses=row['whole_output_membership'];absent=[int(k) for k,v in statuses.items() if v['status']=='absent']
        if case=='D1_subset_fork':check('boundary/'+case+'/'+method,absent,expected['boundary_D1_original_absent_lanes'] if method=='original' else [])
        elif case.startswith('V3'):
            check('boundary/V3_absent',absent,[])
            rejects=sum(e.get('rejected',False) for e in raw['events'] if e['stage']=='mature_reduction')
            check('boundary/V3_rejections',rejects,1)
            heuristics.append(dict(rule='rejection_is_loss',case=case,rule_conclusion='harmful_omission' if rejects else 'no_flag',
                independent_result='both feasible designated branch positions retained in whole union',failure_mode='false_harm_attribution',
                evidence=src,candidate_rejections=rejects))
        else:check('boundary/V5_status',[v['status'] for v in statuses.values()],['unresolved','unresolved'])
        event_rows('B-D1',case,method,src,raw['events'])
    witnesses.append(dict(id='boundary_stationary',groups=['B-D1','B-native-D1'],lanes=[2,3],front_ds=8,rear_ds=11,v=0,a=0,
        feasibility='Body within hidden ds region; 1D prescribed observation field, not rendered sensor.',
        restrictions='Only specified stationary positions; unresolved truncated output remains unresolved.'))
    # Shared primitive discrepancy, independently evaluate the explicit 1D math.
    vel=read('runs/semantic_manuscript_audit_v1/velocity_audit.json');path=[]
    for t in [F(0),F(1,2),F(1)]:
        q=-F(23,2)+6*t+2*t*t;v=6+4*t
        path.append(dict(t=float(t),q=float(q),v=float(v),hidden=not visible_hit(q,fields[str(float(t))])))
    check('moving_witness_feasible',all(x['hidden'] and 0<=x['v']<=15 for x in path))
    cap=math.sqrt(97)
    check('independent_native_algebra_matches_saved',abs(cap-vel['native_cap'])<1e-12)
    common=[r['steps'][2]['shadows'] for r in old_records.values()]
    same=all(x==common[0] for x in common)
    check('four_method_position_output_consensus_at_t1',same)
    check('speed_exceeds_shared_cap',path[-1]['v']>cap)
    check('saved_native_velocity_rows_all_exclude',all(not x['covered'] and not x['translated_covered'] for x in vel['rows']))
    witnesses.append(dict(id='moving_velocity',group='B-velocity',path=path,acceleration=4,
        independent_cap=cap,cap_squared=97,scope='1D front state with length3 footprint; native velocity algebra audited from source, not rerun',
        feasibility='feasible',position='present',speed='absent_under_recorded_native_envelope'))
    heuristics.append(dict(rule='patch_consensus',case='B-velocity/t1',rule_conclusion='semantics_correct' if same else 'no_consensus',
        independent_result='feasible v=10 exceeds shared native cap sqrt(97)',failure_mode='false_reassurance',
        evidence='runs/semantic_manuscript_audit_v1/velocity_audit.json',consensus_methods=list(old_records),cap=cap))
    # Full bounded native discovery corpus: every raw file included, no new run.
    native_counts=collections.Counter();missing_cases=set();primary=[];native_missing=[]
    for name in sorted(z.namelist()):
        if name.startswith(NATIVE+'development/D_') and name.endswith('.json') and '__plain' not in name:
            raw=read(name);primary.append((name,raw));native_counts['primary_conditions']+=1
            strict=0;candidate_coverage=collections.defaultdict(set)
            for ordinal,e in enumerate(raw['events']):
                if e.get('stage')!='mature_reduction':continue
                candidate=e['candidate'];cs=signature(candidate)
                subset=any(not s['risk_bound'] and s['root']['id']==candidate['root']['id'] and
                    s['root'].get('ds_out')==candidate['root'].get('ds_out') and signature(s)<cs for s in e['retained'])
                actual=bool(e['rejected'] and not candidate['risk_bound'] and subset)
                check('strict_subset_flag/%s/%d'%(raw['case'],ordinal),actual,e['strict_subset_rejection'])
                strict+=int(actual)
                if actual:
                    for lane in [2,3]:
                        if position([candidate],lane,8,{1:20,2:20,3:20,100:20,101:20},True)['position_present']:
                            candidate_coverage[e['t']].add(str(lane))
            native_counts['strict_subset_events']+=strict
            native_counts['strict_subset_conditions']+=int(strict>0)
            recovered_epochs=[];harmful_epochs=[]
            for i,ep in enumerate(raw['epochs']):
                native_counts['primary_epoch_updates']+=1
                if 'mature_only_off_same_input' in ep:native_counts['mature_only_epoch_replays']+=1
                # All possible native schedule observations around the body are
                # bounded away: c<=6, islands end<=6.5, upper visible starts15.
                cfg=raw['schedule'][i];feasible=all(0<=cfg[j][0]<=6 and cfg[j][1] in [0,1,2] for j in [1,2])
                row=output_row('B-native-D1',raw['case'],'original',name,i,ep['t'],ep['final_forest'],
                    {1:20,2:20,3:20,100:20,101:20},[2,3],{'status':'feasible' if feasible else 'unresolved',
                    'basis':'stationary body ds[8,11] remains outside all prescribed nearest-sample visible cells'},
                    ep['t']+.25 if i<4 else None,ep['predicted_input'],ignore_forward=True)
                for lane,mem in row['whole_output_membership'].items():
                    stored=ep['witness_membership'][lane]
                    check('native_position/%s/%s/%s'%(raw['case'],ep['t'],lane),
                        [mem['position_present'],mem['absence_supported']],[stored['present'],stored['absence_supported']])
                    if mem['status']=='absent':
                        native_counts['missing_witness_times']+=1;missing_cases.add(raw['case'])
                        native_missing.append(dict(case=raw['case'],t=ep['t'],lane=int(lane),
                            cause='visited_suppression_representative' if raw['case']=='D_template_000' and ep['t']==.25 else 'unresolved',
                            evidence=name))
                if 'mature_only_off_same_input' in ep:
                    repaired=ep['mature_only_off_same_input'];recovered=[]
                    for lane in [2,3]:
                        cm=position(repaired['final_forest'],lane,8,{1:20,2:20,3:20,100:20,101:20},True)
                        saved=repaired['witness_membership'][str(lane)]
                        check('native_mature_off_position/%s/%s/%s'%(raw['case'],ep['t'],lane),
                            [cm['position_present'],cm['absence_supported']],[saved['present'],saved['absence_supported']])
                        if row['whole_output_membership'][str(lane)]['status']=='absent' and cm['position_present']:recovered.append(str(lane))
                    check('native_recovered_witnesses/%s/%s'%(raw['case'],ep['t']),recovered,ep['recovered_witnesses'])
                    if recovered:recovered_epochs.append(ep['t'])
                    if set(recovered)&candidate_coverage[ep['t']]:harmful_epochs.append(ep['t'])
            check('native_positive_epochs/'+raw['case'],recovered_epochs,raw['positive_epochs'])
            native_counts['positive_harmful_D1_conditions']+=int(bool(harmful_epochs))
            plain_name=name[:-5]+'__plain.json'
            if plain_name in z.namelist():
                plain=read(plain_name);native_counts['plain_parity_replays']+=1
                check('native_plain_parity/'+raw['case'],[e['final_forest'] for e in raw['epochs']],[e['final_forest'] for e in plain['epochs']])
    native_counts['missing_conditions']=len(missing_cases)
    attr=read(NATIVE+'representative_attribution/summary.json')
    native_counts['cause_adjudicated_conditions']=1
    native_counts['cause_unresolved_conditions']=len(missing_cases-{'D_template_000'})
    for a in attr:
        src=NATIVE+'representative_attribution/'+a['variant']+'.json';raw=read(src)
        check('attribution_same_prefix/'+a['variant'],[a['prior_epoch_matches'],a['target_input_matches']],[True,True])
        target=next(ep for ep in raw['epochs'] if ep['t']==.25)
        actual=[position(target['final_forest'],l,8,{1:20,2:20,3:20,100:20,101:20},True)['status'] for l in [2,3]]
        check('attribution_recovery/'+a['variant'],actual,['present','present'] if a['variant']=='visited_only_off_at_target' else ['absent','absent'])
        event_rows('B-native-D1','D_template_000',a['variant'],src,raw.get('reduction_site_events',raw['events']))
    # V3: independently inspect the actual archived target evidence, rather than
    # extending one condition-level attribution to every witness-time in it.
    attr_base=NATIVE+'representative_attribution/'
    archived_original=read(NATIVE+'development/D_template_000.json')
    attribution_scope=[]
    variants=['original_v2_trace','admission_only_off_at_target',
              'visited_only_off_at_target','mature_only_off_at_target']
    original_source=z.read(attr_base+'original_v2_trace.py').decode()
    visited_source=z.read(attr_base+'visited_only_off_at_target.py').decode()
    old_condition='            if bound_lane_id in bwd_visited_lane:'
    target_condition='            if t != .25 and bound_lane_id in bwd_visited_lane:'
    check('v3/visited_source_single_target_condition_occurrence',original_source.count(old_condition),1)
    check('v3/visited_source_only_change_is_t025_gate',
          visited_source,original_source.replace(old_condition,target_condition))
    for variant in variants:
        raw=read(attr_base+variant+'.json')
        prefix=[ep for ep in raw['epochs'] if ep['t']<.25]
        original_prefix=[ep for ep in archived_original['epochs'] if ep['t']<.25]
        target=next(ep for ep in raw['epochs'] if ep['t']==.25)
        original_target=next(ep for ep in archived_original['epochs'] if ep['t']==.25)
        check('v3/raw_prefix/'+variant,prefix,original_prefix)
        check('v3/raw_target_input/'+variant,target['predicted_input'],original_target['predicted_input'])
        check('v3/raw_observation_schedule/'+variant,raw['schedule'],archived_original['schedule'])
        check('v3/raw_completed/'+variant,raw['status'],'completed')
        # Independent narrow decoder for this one target: both witness lanes
        # occur only as finite terminal InBound/InOutBound nodes.  It does not
        # use position(), saved witness_membership or summary status fields.
        spans={2:[],3:[]};unsupported=[]
        def target_leaves(node):
            children=node.get('children') or []
            if node['id'] in spans:
                if children or node['type'] not in ['InBound','InOutBound']:
                    unsupported.append(node)
                else:
                    spans[node['id']].append([0 if node['type']=='InBound' else node['ds_out'],node['ds_in']])
            for child in children:target_leaves(child)
        for shadow in target['final_forest']:
            if shadow['risk_bound']:continue
            if any(x is None for x in shadow['leaf_depth']):unsupported.append('truncated_leaf')
            target_leaves(shadow['root'])
        check('v3/target_narrow_decoder_support/'+variant,unsupported,[])
        actual=[any(lo<=8<=hi for lo,hi in spans[lane]) for lane in [2,3]]
        wanted=[variant=='visited_only_off_at_target']*2
        check('v3/target_independent_interval_membership/'+variant,actual,wanted)
        attribution_scope.append(dict(variant=variant,target_time=.25,
            source=attr_base+variant+'.json',prefix_update_times=[ep['t'] for ep in prefix],
            exact_prefix_parity=prefix==original_prefix,
            exact_target_input_parity=target['predicted_input']==original_target['predicted_input'],
            exact_observation_schedule_parity=raw['schedule']==archived_original['schedule'],
            independently_decoded_intervals=spans,position_membership=actual,
            supported_cause_scope='D_template_000 at t=0.25, lane2/3 only; subsequent epochs are not same-prefix attributions'))
    adjudicated=[(x['case'],x['t'],x['lane']) for x in native_missing if x['cause']!='unresolved']
    check('v3/exact_adjudicated_witness_times',adjudicated,[('D_template_000',.25,2),('D_template_000',.25,3)])
    later=[x for x in native_missing if x['case']=='D_template_000' and x['t']>.25]
    check('v3/later_D000_witness_time_count',len(later),6)
    check('v3/later_D000_cause_unresolved',[(x['t'],x['lane'],x['cause']) for x in later],
          [(t,lane,'unresolved') for t in [.5,.75,1.] for lane in [2,3]])
    check('v3/overall_missing_cause_counts',dict(collections.Counter(x['cause'] for x in native_missing)),
          {'visited_suppression_representative':2,'unresolved':102})
    # This is a correction relative to the immutable, delivered V2 artifact.
    # Verify every other normalized scientific record is unchanged.
    parity=[]
    for filename,current in [('outputs.jsonl',outputs),('events.jsonl',events),('queries.jsonl',queries),
                             ('witnesses.json',witnesses),('heuristics.json',heuristics),('source_lineage.json',lineage)]:
        path=args.artifact/'validation_v2'/filename
        previous=[json.loads(line) for line in path.read_text().splitlines()] if filename.endswith('.jsonl') else json.loads(path.read_text())
        if filename=='source_lineage.json':
            previous=[row for row in previous if not row['archived_path'].endswith('/inspect_d05.py')]
        same=current==previous
        check('v3/unchanged_normalized/'+filename,same)
        parity.append(dict(path=filename,records=len(current),unchanged=same,
                           immutable_v2_sha256=sha(path.read_bytes()),
                           comparison_scope='Retained paper source entries; two omitted D05 tracing scripts excluded' if filename=='source_lineage.json' else 'All records'))
    prior_missing=json.loads((args.artifact/'validation_v2'/'native_unresolved_inventory.json').read_text())
    check('v3/inventory_same_row_count',len(native_missing),len(prior_missing))
    changes=[]
    for previous,current in zip(prior_missing,native_missing):
        delta={key:{'before':previous.get(key),'after':current.get(key)}
               for key in set(previous)|set(current) if previous.get(key)!=current.get(key)}
        if delta:changes.append(dict(case=current['case'],t=current['t'],lane=current['lane'],delta=delta))
    wanted_changes=[dict(case='D_template_000',t=t,lane=lane,
        delta={'cause':{'before':'visited_suppression_representative','after':'unresolved'}})
        for t in [.5,.75,1.] for lane in [2,3]]
    check('v3/exactly_six_cause_only_corrections',changes,wanted_changes)
    dump(out/'attribution_scope_audit.json',dict(target_time=.25,variants=attribution_scope,
        adjudicated_witness_times=adjudicated,later_D000_unresolved_witness_times=later,
        cause_counts=dict(collections.Counter(x['cause'] for x in native_missing)),
        condition_count_interpretation='1 missing condition has at least one adjudicated target; 34 have none. The first condition also contains 6 unresolved witness-times.',
        new_native_runs=0))
    dump(out/'version_parity.json',dict(parent_version='validation_v2',unchanged_records=parity,
        inventory_changes=changes,raw_archive_unchanged=True,
        archive_sha256=manifest['archive_sha256'],new_native_runs=0))
    wrapper=read(NATIVE+'wrapper_initialization_check/summary.json')
    native_counts['legal_wrapper_sequences']=len(wrapper);native_counts['legal_wrapper_updates']=sum(x['native_wrapper_updates'] for x in wrapper)
    check('two_legal_wrapper_controls',all(x['all_post_update_parity'] and x['legal_ego_waypoint'] and x['native_initial_inbound_ds']==17.5 for x in wrapper))
    check('native_D1_denominators',dict(native_counts),expected['native_D1'])
    write_rows(out/'outputs.jsonl',outputs);write_rows(out/'events.jsonl',events);write_rows(out/'queries.jsonl',queries)
    dump(out/'witnesses.json',witnesses);dump(out/'heuristics.json',heuristics);dump(out/'native_unresolved_inventory.json',native_missing)
    dump(out/'source_lineage.json',lineage)
    with (out/'heuristic_limits.csv').open('w') as f:
        keys=['rule','case','rule_conclusion','independent_result','failure_mode','evidence'];w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(heuristics)
    dump(out/'validation_results.json',dict(schema='spais.e3.validation.v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        python=platform.python_version(),validator_sha256=sha(pathlib.Path(__file__).read_bytes()),
        archive_sha256=manifest['archive_sha256'],expected_sha256=sha((args.artifact/'expected.json').read_bytes()),
        new_native_runs=0,checks=len(checks),failed=sum(not x['pass_'] for x in checks),
        failed_checks=[x for x in checks if not x['pass_']],checks_detail=checks,
        normalized_record_counts={'outputs':len(outputs),'events':len(events),'queries':len(queries),'witness_definitions':len(witnesses)},
        historical_denominators={'sensor':dict(sensor_cohort),'native_D1':dict(native_counts)},
        scientific_limits='Retrospective designated-witness checks, no detector accuracy, global proof or new native experiment.'))
    (out/'source_executed.py').write_bytes(pathlib.Path(__file__).read_bytes())
    print(json.dumps({'checks':len(checks),'failed':sum(not x['pass_'] for x in checks),'outputs':len(outputs),'queries':len(queries),'output':str(out)},indent=2))
    if any(not x['pass_'] for x in checks):
        raise SystemExit(1)

if __name__=='__main__':main()
