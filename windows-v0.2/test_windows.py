"""Public minimal regression cases; no solver implementation or private data."""
import argparse,json,copy
from pathlib import Path
from fractions import Fraction
from v51 import Solver
parser=argparse.ArgumentParser();parser.add_argument('--cpu-only',action='store_true');args=parser.parse_args();records=[]
def one(c,lo,up,rhs,row,col,value,integer=None):
 return dict(c=c,lower=lo,upper=up,binary=[False]*len(c),integer=[False]*len(c)if integer is None else integer,rhs=rhs,row=row,col=col,value=value)
cases=[
 ('infeasible_LP',one([1],[0],[2],[1,0],[0,1],[0,0],[1,-1]),'infeasible'),
 ('integer_infeasible',one([1],[0],[1],[.5,-.5],[0,1],[0,0],[1,-1],[True]),'infeasible'),
 ('integer_without_upper',one([1],[0],[None],[1],[0],[0],[1],[True]),'optimal'),
 ('v01_cancellation_regression',one([0,0,0],[10000,1,10000],[10000,1,10000],[0],[0,0,0],[0,1,2],[1e12,-1,-1e12],[True]*3),'infeasible'),
 ('maximize',dict(one([1],[0],[3],[1],[0],[0],[1],[True]),objective_sense='max'),'optimal'),
 ('unbounded_box',one([-1],[0],[None],[],[],[],[]),'unbounded')]
with Solver(seconds=2,backend='cpu'if args.cpu_only else'gpu',proof_seconds=1.)as solver:
 for name,model,expected in cases:
  r=solver.solve(model);assert r['status']==expected,(name,r)
  assert solver.verify_certificate(model,r['certificate']).get('verified'),name
  if expected=='optimal':assert r['optimality_proven']and r['relative_gap']<=1e-7
  bad=copy.deepcopy(r['certificate']);bad['format']='invalid';assert not solver.verify_certificate(model,bad).get('verified')
  records.append(dict(test=name,passed=True,status=r['status'],gpu_used=r.get('metadata',{}).get('gpu_used',False),certificate_verified=True));print(name,r['status'],flush=True)
 if not args.cpu_only:
  hardware=solver.general_gpu_self_test();records.append(dict(test='general_GPU_hardware',result=hardware));assert hardware.get('passed'),hardware
  hardware=solver.self_test(gpu=True);records.append(dict(test='structured_GPU_hardware',result=hardware));assert hardware.get('passed'),hardware
result=dict(passed=True,cpu_only=args.cpu_only,records=records)
Path('windows_check_result.json').write_text(json.dumps(result,indent=2));print('PASSED. Send windows_check_result.json for hardware confirmation.')
