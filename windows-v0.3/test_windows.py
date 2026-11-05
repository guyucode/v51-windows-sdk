"""Public client regression. No solver implementation; standard-library only."""
import argparse,copy,itertools,json,math,random,sys,time,traceback
from pathlib import Path
from v51 import Solver,LPBatch
p=argparse.ArgumentParser();p.add_argument('--cpu-only',action='store_true');p.add_argument('--warp-lp',action='store_true');args=p.parse_args()
report={'version':'0.3.0-windows-preview','tests':[],'GPU_tests_requested':not args.cpu_only and not args.warp_lp,'WARP_validation_requested':args.warp_lp,'Windows_runtime':sys.platform=='win32'}
def run(name,fn,group):
    start=time.perf_counter()
    print('START',name,flush=True)
    report['passed']=False;report['run_completed']=False;Path('windows_check_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        details=fn();report['tests'].append(dict(name=name,group=group,passed=True,seconds=time.perf_counter()-start,details=details));print('PASS',name,flush=True)
    except Exception as exc:
        report['tests'].append(dict(name=name,group=group,passed=False,seconds=time.perf_counter()-start,error=str(exc),traceback=traceback.format_exc()));print('FAIL',name,str(exc),flush=True)
    Path('windows_check_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def model(c,lo,up,rhs,row,col,value,integer=None,sense='min'):
    return dict(c=c,lower=lo,upper=up,rhs=rhs,row=row,col=col,value=value,integer=integer or [False]*len(c),objective_sense=sense)
base=model([1.,2.],[0.,0.],[4.,4.],[1.],[0,0],[0,1],[1.,1.])
contradiction=model([1.],[0.],[4.],[2.,-1.],[0,1],[0,0],[1.,-1.])
fractional=model([1.],[0.],[1.],[.5,-.5],[0,1],[0,0],[1.,-1.],[True])
cancellation=model([0.,0.,0.],[10000.,1.,10000.],[10000.,1.,10000.],[0.],[0,0,0],[0,1,2],[1e12,-1.,-1e12],[True]*3)
with Solver(seconds=2.,backend='cpu',proof_seconds=1.)as s:
    print('START diagnostics',flush=True)
    report['diagnostics']=s.diagnostics()
    print('PASS diagnostics',flush=True)
    def check_certificate(m,status,objective=None):
        r=s.solve(m);assert r['status']==status and r['proof_complete'],r
        assert s.verify_certificate(m,r['certificate'])['verified'],r
        if objective is not None:assert r['validated']and r['optimality_proven']and abs(r['objective']-objective)<1e-7,r
        else:assert not r['validated'],r
        bad=copy.deepcopy(r['certificate']);bad['format']='invalid';assert not s.verify_certificate(m,bad)['verified']
        return dict(status=r['status'],CPU_exact_proof=r['cpu_exact_search_for_proof'],certificate_verified=True)
    run('LP_infeasible_certificate',lambda:check_certificate(contradiction,'infeasible'),'certificate')
    run('integer_only_infeasible_certificate',lambda:check_certificate(fractional,'infeasible'),'certificate')
    run('v01_false_feasible_regression',lambda:check_certificate(cancellation,'infeasible'),'certificate')
    run('LP_optimal_certificate',lambda:check_certificate(base,'optimal',1.),'certificate')
    maximum=copy.deepcopy(base);maximum['objective_sense']='max'
    run('max_objective_certificate',lambda:check_certificate(maximum,'optimal',12.),'certificate')
    run('integer_without_upper_bound',lambda:check_certificate(model([1.],[0.],[None],[1.],[0],[0],[1.],[True]),'optimal',1.),'certificate')
    run('unbounded_box_certificate',lambda:check_certificate(model([-1.],[0.],[None],[],[],[],[]),'unbounded'),'certificate')
    def brute_regression():
        rng=random.Random(1303)
        for k in range(24):
            n=3;A=[[rng.randint(-3,3)for _ in range(n)]for _ in range(4)];b=[rng.randint(-4,5)for _ in A];c=[rng.randint(-3,3)for _ in range(n)];sense='max'if k%3==0 else'min'
            feasible=[sum(a*x for a,x in zip(c,y))for y in itertools.product(range(4),repeat=n)if all(sum(a*x for a,x in zip(row,y))>=rhs for row,rhs in zip(A,b))]
            m=model(c,[0]*n,[3]*n,b,[i for i,row in enumerate(A)for a in row],[j for row in A for j in range(n)],[a for row in A for a in row],[True]*n,sense)
            check_certificate(m,'optimal'if feasible else'infeasible',(max(feasible)if sense=='max'else min(feasible))if feasible else None)
        return {'cases':24,'oracle':'exhaustive enumeration; client tests only'}
    run('standard_integer_bruteforce',brute_regression,'certificate')
    def exact_numeric_consistency():
        B=2**53
        m=model([1.],[0.],[float(B+8)],[float(3*B+8)],[0],[0],[3.],[True]);m['offset']=-float(B)
        with Solver(seconds=.1,backend='cpu',proof_seconds=.1)as bounded:
            r=bounded.solve(m)
        assert not r['optimality_proven']and not r['proof_complete'],r
        assert r['status']!='optimal',r
        return dict(status=r['status'],objective=r.get('objective'),numeric_point_not_falsely_optimal=True)
    run('exact_proof_numeric_solution_consistency',exact_numeric_consistency,'certificate')
def device_ran(r):
    meta=r.get('metadata',{})
    if args.warp_lp:return meta.get('Direct3D_dispatch_executed')and meta.get('CPU_software_shader')and not meta.get('GPU_executed')
    return meta.get('GPU_executed')and not meta.get('CPU_Newton')
if not args.cpu_only:
    def milp_check(m):
        with Solver(seconds=2.,backend='warp_validation'if args.warp_lp else'gpu',proof_seconds=0.)as s:
            r=s.solve(m);assert r.get('steps',0)>0,r
            if args.warp_lp:assert r['metadata']['CPU_software_shader']and not r['metadata']['gpu_used'],r
            else:assert r['metadata']['gpu_used'],r
            assert r['validated']and not r['optimality_proven'],r
            return dict(status=r['status'],backend=r['backend'],gpu_used=not args.warp_lp,CPU_software_shader=args.warp_lp)
    run('GPU_standard_binary',lambda:milp_check(dict(base,binary=[True,True])),'GPU_MILP')
    general=model([1.,2.],[0.,0.],[3.,3.],[2.],[0,0],[0,1],[2.,3.],[True,True])
    run('GPU_standard_general_integer',lambda:milp_check(general),'GPU_MILP')
    mixed=model([1.,.25],[0.,0.],[3.,3.],[1.],[0,0],[0,1],[2.,1.],[True,False])
    run('GPU_standard_mixed_integer',lambda:milp_check(mixed),'GPU_MILP')
    def negative_milp(m):
        with Solver(seconds=2.,backend='warp_validation'if args.warp_lp else'gpu',proof_seconds=0.)as s:
            r=s.solve(m);assert r.get('steps',0)>0,r
            assert not r['validated']and not r['optimality_proven']and not r['proof_complete'],r
            assert r['status']not in('infeasible','optimal'),r
            assert r['cpu_exact_search_for_proof']is False,r
            if args.warp_lp:assert r['metadata']['CPU_software_shader']and not r['metadata']['gpu_used'],r
            else:assert r['metadata']['gpu_used'],r
            return dict(status=r['status'],proof_disabled=True,false_feasible_rejected=True,metadata=r['metadata'])
    run('GPU_v01_false_feasible_without_proof',lambda:negative_milp(cancellation),'GPU_MILP')
    run('GPU_integer_fractional_infeasible_without_proof',lambda:negative_milp(fractional),'GPU_MILP')
    def lp_batch(B):
        models=[]
        for k in range(B):
            m=copy.deepcopy(base);m['rhs']=[1.+k/16.];m['objective_sense']='max'if k%3==1 else'min';models.append(m)
        with LPBatch(base,capacity=B,validation_backend="warp"if args.warp_lp else None)as session:
            r=session.solve(models,seconds=2.);assert device_ran(r),r
            assert r['metadata']['per_Newton_host_reads']==0,r
            with Solver(backend='cpu')as verifier:
                for m,item in zip(models,r['results']):
                    expected=12. if m.get('objective_sense')=='max'else m['rhs'][0]
                    assert item['qualified']and abs(item['objective']-expected)<1e-5,item
                    assert item['bound_direction']==('upper'if m.get('objective_sense')=='max'else'lower'),item
                    assert not item['optimality_proven']and not item['proof_complete'],item
                    assert verifier.verify_certificate(m,item['bound_certificate'])['verified']
                    bad=copy.deepcopy(item['bound_certificate']);bad['lower_bound']=1e20
                    assert not verifier.verify_certificate(m,bad)['verified']
            reverse=session.solve(models[::-1],seconds=2.)
            assert all(x['qualified']for x in reverse['results']),reverse
            assert all(abs(a['objective']-b['objective'])<1e-6 for a,b in zip(r['results'][::-1],reverse['results'])),reverse
            changed=copy.deepcopy(base);changed['value']=[2.,1.];miss=session.solve([changed]);assert miss.get('status')=='api_error'and'template_miss'in miss.get('error',''),miss
            return dict(qualified=B,reordered_qualified=B,online_seconds=r['online_seconds'],offline_seconds=session.offline_full_call_seconds,metadata=r['metadata'])
    for B in (1,8,16):run('GPU_LP_batch_'+str(B),lambda B=B:lp_batch(B),'GPU_LP')
    def negative_batch():
        feasible=copy.deepcopy(contradiction);feasible['rhs']=[.5,-1.]
        with LPBatch(feasible,capacity=2,validation_backend="warp"if args.warp_lp else None)as session:
            r=session.solve([feasible,contradiction]);assert device_ran(r),r
            a,b=r['results'];assert a['qualified'],a
            assert not b['validated']and not b['qualified']and not b['optimality_proven']and not b['proof_complete'],b
            assert b['status']=='unknown',b
            return dict(feasible=a['status'],infeasible_without_certificate=b['status'],device_failure_not_infeasibility=True)
    run('GPU_LP_mixed_feasible_infeasible',negative_batch,'GPU_LP')
    def unbounded_lp():
        m=model([-1.],[0.],[None],[],[],[],[])
        with LPBatch(m,capacity=1,validation_backend="warp"if args.warp_lp else None)as session:
            r=session.solve([m]);assert device_ran(r),r
            item=r['results'][0];assert not item['qualified']and not item['optimality_proven']and not item['proof_complete'],item
            return dict(status=item['status'],unbounded_not_misreported_optimal=True)
    run('GPU_LP_unbounded_no_false_optimum',unbounded_lp,'GPU_LP')
report['run_completed']=True
report['passed']=all(t['passed']for t in report['tests']);report['GPU_tests_executed']=not args.cpu_only and not args.warp_lp
report['WARP_tests_executed']=args.warp_lp
if args.warp_lp:
    for t in report['tests']:
        if t['group']=='GPU_MILP':t['group']='Windows_Direct3D_WARP_MILP';t['name']=t['name'].replace('GPU_','WARP_')
        if t['group']=='GPU_LP':t['group']='Windows_Direct3D_WARP_LP';t['name']=t['name'].replace('GPU_LP','WARP_LP')
Path('windows_check_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Saved windows_check_result.json; GPU tests skipped'if args.cpu_only else'Saved windows_check_result.json')
sys.exit(0 if report['passed']else 1)
