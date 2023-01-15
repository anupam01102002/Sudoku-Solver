# -*- coding: utf-8 -*-
'''
*A simple problem solver written in pure Python*

Module provides an easy way to solve various problems that require
calculations. Lets imagine a problem formulated in
a text file using a some template language. Some places
within the problem formulation text coresspond to variables
that have default values. What does `to solve a problem` mean in this context?
To solve the problem is to 1) define output template (used to render solution), 2) write code
that exploits input variables, 3) setup output variables in the code and, finally, 4) 
render the solution template.
With help of solver classes these steps of getting a problem solution
can be made easily.

Solver features:
    * arbitrary and independent input and output markups
      used in problem formulation and solution templates.
    * ability of asynchronous problem solving (Celery is required).
    * heuristic testing of problem solvability.
    * using all of Python computational ability to solve your problems.
    * using jinja2 template language to produce dynamic parts of a problem
      formulation/solution.

:Example:

    Test problem. My name is Dmitry. I have 100 $.
    I want to buy several papers. Each paper worth is 5 $. How many papers can
    I buy?

    Test problem  (abstraction level) ::

    test_problem_template_formulation = """
    My name is {{username}}. I have {{total}} $.
    I want to buy several papers. Each paper worth is {{paper_cost}}$.
    How many papers can I buy?
    """

    test_problem_solution_code = """
    OUTPUTS['result']=INPUTS['total']/INPUTS['paper_cost']
    OUTPUTS['name'] = INPUTS['username']
    """

    test_problem_output_template="""
    My name is {{name}} and answer is {{result}}.
    """

    from solver import Task, Solver

    task = Task(test_problem_template_formulation,
                default_vals={'username': 'Dmitry',
                'total': 100, 'paper_cost': 20},
                solution_template=test_problem_output_template,
                code = test_problem_solution_code
                )
    psolver = Solver(task)

    # solve the problem
    psolver.solve()

    # or you can try to solve problem asynchronously instead
    # if error occur .solve() method will be invoked by default.
    psolver.async_solve()

    #Prior to get results, check for problem solution is ready
    #(This step is required, when solving problem asynchronously)
    if psolver.is_solved:
        task.render_outputs() # Render output template
        print(task.output) # Print renedered template or do something else

'''

__all__=('Solver', 'Task', 'get_celery_worker_status')

import ast
import datetime
import pickle
import uuid
import warnings

from jinja2 import Environment, Template
from jinja2.exceptions import TemplateSyntaxError
from jinja2.meta import find_undeclared_variables
import six

from .expts import TemplateOutputSyntaxError, UnsolvableProblem


if six.PY3:
    from io import BytesIO
else:
    from StringIO import StringIO


def get_celery_worker_status():
    ERROR_KEY = "ERROR"
    try:
        from celery import Celery
        app = Celery()
        app.config_from_object('celeryconf')
        insp = app.control.inspect()
        d = insp.stats()
        if not d:
            d = {ERROR_KEY: 'No running Celery workers were found.'}
    except IOError as e:
        from errno import errorcode
        msg = "Error connecting to the backend: " + str(e)
        if len(e.args) > 0 and errorcode.get(e.args[0]) == 'ECONNREFUSED':
            msg += ' Check that the RabbitMQ server is running.'
        d = {ERROR_KEY: msg}
    except ImportError as e:
        d = {ERROR_KEY: str(e)}
    except Exception as x:
        d = {ERROR_KEY: str(x)}
    return d

WORKER_STATUS_ERROR = True if get_celery_worker_status().get('ERROR', False)\
                        else False


class Task:
    '''Base class to handle a problem instance.'''

    def __init__(self, content, solution_template='',
                 default_vals=None, code=''):
        # public properties
        self.content = content
        self.output = ''
        self.default_vals = default_vals
        self.code = code
        self.output_vals = {}

        # private properties
        self._env = Environment()
        self._templateerror = False
        self.solution_template = solution_template

        try:
            self._allvars = find_undeclared_variables(
                            self._env.parse(self.content))
        except TemplateSyntaxError:
            self._allvars = set([])
            self._templateerror = True
        if not bool(self._allvars):
            self._allvars = set([])

        self._template_output_error = False

        try:
            self._all_output_vars = find_undeclared_variables(
                                    self._env.parse(self.solution_template))
        except TemplateSyntaxError:
            self._all_output_vars = {}
            self._template_output_error = True

    def render_outputs(self):
        if self._template_output_error:
            raise TemplateOutputSyntaxError('Check output\
            template for correctness.')

        if self._all_output_vars and not\
                self._all_output_vars.issubset(set(self.output_vals.keys())):
            warnings.warn('Not all variables defined in `output_vals`.',
                          SyntaxWarning)

        if not self._template_output_error and not\
                self._all_output_vars:
            self.output = self.solution_template
        else:
            temp = Template(self.solution_template)
            self.output = temp.render(**self.output_vals)

    def is_content_valid(self):
        '''Validate input template. '''

        if not self.content:
            return True

        if self._templateerror:
            return False

        return True

    def is_state_correct(self):
        '''Validate correctness of a problem.

        A problem treated as a correct problem, if:
            1) Content template for a problem is valid, see `is_content_valid`\
            method;
            2) All variables defined in the content has default values;

        '''

        if not self.is_content_valid():
            return False

        if self._allvars:
            if self._allvars.issubset(set(self.default_vals.keys())):
                return True
            else:
                return False
        else:
            return True

    @property
    def is_solved(self):
        '''returns True if `output_vals` exists otherwise False'''

        return True if self.output_vals else False


class Solver:
    '''Main class for getting problem solutions.'''

    def_input_code_PY2 = '''
import pickle
from StringIO import StringIO

_raw_input = ''
_tmpvar = StringIO(_raw_input)

INPUTS = pickle.load(_tmpvar)

OUTPUTS = {}
    '''
    def_input_code_PY3 = '''
import pickle
from io import BytesIO

_raw_input = b''
_tmpvar = BytesIO(_raw_input)

INPUTS = pickle.load(_tmpvar)

OUTPUTS = {}
'''
    def_input_code = def_input_code_PY3 if six.PY3 else def_input_code_PY2

    def __init__(self, task, preamble='', postamble=''):
        '''Create a solver instance.'''

        self.task = task
        self.preamble = preamble
        self.postamble = postamble  # NOTE: currently not used.
        self._code = '# -*- coding: utf-8 -*- \n\n' + self.preamble +\
            '\n\n' + Solver.def_input_code + '\n\n' +\
            self.task.code + '\n\n' + self.postamble

        self.created = datetime.datetime.now()
        self.start = None
        self.end = None
        self.id = uuid.uuid4().hex
        self._async_obj = None

    def is_solvable(self, silent=True):
        '''Heuristic test for a task solvability.

        Solvable task should have either empty or compilable code.
        This function tries to parse code-block of your problem with
        ``ast`` module
        '''

        if not self.task.code:
            return True

        retvalue = True
        if silent:
            try:
                ast.parse(self._code)
                retvalue = True
            except:
                retvalue = False
            finally:
                return retvalue
        else:
            ast.parse(self._code)
            return retvalue

    def solve(self):
        '''Solve current problem.


        '''

        if not self.is_solvable():
            raise UnsolvableProblem

        if six.PY3:
            a_task_serial = BytesIO()
            pickle.dump(self.task.default_vals, a_task_serial)
        else:
            a_task_serial = StringIO()
            pickle.dump(self.task.default_vals, a_task_serial)
        a_task_serial.seek(0)
        pcode = ast.parse(self._code, mode='exec')
        transformer = ast.NodeTransformer()
        newcode = transformer.visit(pcode)
        for item in newcode.body:
            if isinstance(item, ast.Assign):
                if any(map(lambda x: getattr(x, 'id', None) == '_raw_input',
                           item.targets)):
                    if six.PY3:
                        item.value = ast.Bytes(a_task_serial.read())
                    else:
                        item.value = ast.Str(a_task_serial.read())
        newcode = ast.fix_missing_locations(newcode)
        cobj = compile(newcode, '<string>', mode='exec')
        evalspace = {}
        try:
            self.start = datetime.datetime.now()
            six.exec_(cobj, evalspace)
            self.end = datetime.datetime.now()
        finally:
            if not self.end:
                self.start = None
                self.end = None
        if evalspace.get('OUTPUTS'):
            self.task.output_vals = evalspace.get('OUTPUTS')

    def async_solve(self):
        '''Try to solve a problem asynchoronously via Celery.

        If Celery is not installed, the function tries
        to get a solution with solve method.
        '''

        if WORKER_STATUS_ERROR:
            self.solve()
        else:
            if not self._async_obj:
                from tasks import solve
                self.start = datetime.datetime.now()
                self._async_obj = solve.delay(self)

    @property
    def is_solved(self):
        '''Solution status. When a problem is solved returns true.

        One need to check status of asynchoronous task via `is_solved`\
        before getting the results.
        '''

        if self._async_obj and not isinstance(self._async_obj, tuple):
            if self._async_obj.ready():
                self.task.output_vals, self.start,\
                    self.end = self._async_obj.result
        return True if self.end else False

    @property
    def total(self):
        '''Total execution time in milliseconds.'''

        if self.start and self.end:
            return float((self.end - self.start).microseconds)/1000.0
        else:
            return None
