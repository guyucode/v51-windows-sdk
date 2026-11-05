"""Public usage example only; solver implementation is in the DLL."""
from v51 import Solver,LPBatch
import copy
model=dict(c=[1.,2.],lower=[0.,0.],upper=[4.,4.],rhs=[1.],row=[0,0],col=[0,1],value=[1.,1.])
milp=copy.deepcopy(model);milp['integer']=[True,False]
with Solver(seconds=.2,backend='gpu',proof_seconds=0)as solver:
    result=solver.solve(milp)
    print('MILP:',result['status'],result.get('objective'),result.get('metadata'))
second=copy.deepcopy(model);second['rhs']=[2.]
with LPBatch(model,capacity=2)as solver:
    result=solver.solve([model,second],seconds=2)
    print('LP batch:',result)
