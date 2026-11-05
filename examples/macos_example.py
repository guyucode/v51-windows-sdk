"""Public toy examples, no private benchmark models."""
import json
from v51 import MILPSolver,LPSolver
lp=dict(c=[1.,2.],offset=0.,lower=[0.,0.],upper=[2.,2.],rhs=[1.],row=[0,0],col=[0,1],value=[1.,1.])
with LPSolver(lp,capacity=2)as solver:
 result=solver.solve([{},dict(rhs=[1.5])]);assert result['status']=='completed',result
 assert len(result['results'])==2 and all(p['qualified']for p in result['results']),result
 assert abs(result['results'][0]['metrics']['objective']-1.)<1e-5
 assert abs(result['results'][1]['metrics']['objective']-1.5)<1e-5
 print('GPU LP:',json.dumps({'passed':True,'objectives':[p['metrics']['objective']for p in result['results']],'seconds':result['python_full_call_seconds']}))
milp=dict(c=[0,0,0,0,1],offset=0,lower=[0,0,0,None,None],upper=[1,1,0,None,None],binary=[True,True,False,False,False],rhs=[1,-1,-8,-9,0],row=[0,0,1,1,2,2,2,3,3,3,4,4],col=[0,1,0,1,0,2,3,1,2,3,3,4],value=[1,1,-1,-1,-10,-1,1,-10,-1,1,-1,1])
r=MILPSolver(seconds=5.).solve(milp);assert r.get('validated'),r
x=r['solution'];assert abs(x[0]+x[1]-1)<1e-7 and max(abs(x[j]-round(x[j]))for j in (0,1))<=1e-7
assert x[3]-10*x[0]>=-8-1e-7 and x[3]-10*x[1]>=-9-1e-7 and x[4]>=x[3]-1e-7
print('GPU MILP:',json.dumps({'passed':True,'objective':r['objective'],'seconds':r['python_full_call_seconds'],'continuous_backend':r['default_continuous_backend']}))
