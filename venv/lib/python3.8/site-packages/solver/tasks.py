
import datetime

from celery import Celery

from .base import Solver
from .expts import InappropriateSolverTypeError


app = Celery()
app.config_from_object('celeryconf')


@app.task
def solve(x):
    if isinstance(x, Solver):
        x.solve()
        x.end = datetime.datetime.now()
        return x.task.output_vals, x.start, x.end
    else:
        raise InappropriateSolverTypeError('Use the instances\
 of class `Solver` instead.')
