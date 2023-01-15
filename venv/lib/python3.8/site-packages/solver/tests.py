from __future__ import print_function

import unittest
import warnings

from .base import Task, Solver
from .expts import TemplateOutputSyntaxError, UnsolvableProblem
import numpy as np


class TestBaseTaskClass(unittest.TestCase):

    def setUp(self):
        self.bad_solver_variable_name = 'turipov'
        self.bad_python_variable_name = '1cot'
        self.valid_python_name = 'acat'
        self.valid_solver_variable_name = 'ivvec_matrix1'

#       Test problem definitions
#       Problem correctness
        self.correct_problem1 = Task(
            '''My name is {{ivstr_name1}}. I am
            {{ivsca_myage}} y.o. Currently, I like the following sequence
            {{ivvec_vec1}}. Also, I like magic squares {{ivmat_mat1}}''',
            default_vals={'ivstr_name1': 'Dmitry',
                          'ivsca_myage': 30.0,
                          'ivvec_vec1': np.random.rand(10),
                          'ivvec_addval': None,
                          'ivmat_mat1': np.random.rand(3, 3)})

        self.incorrect_problem1 = Task(
            '''My name is {{ivstr_name1}}.
            I am {{ivsca_myage}} y.o. Currently, I like the following sequence
            {{ivvec_vec1}}. Also, I like magic squares {{ivmat_mat1}}''',
            default_vals={'ivvec_vec1': range(10),
                          'ivvec_addval': None,
                          'ivmat_mat1': np.random.rand(3, 3)})

#               Problem content validation
        self.invalid_content_problem1 = Task('''My name is {{ivstr_name1}.
         I am {{ivsca_myage}} y.o. Currently, I like the following
         sequence {{ivvec_vec1}}. Also, I like magic squares {{ivmat_mat1}}''')

    def test_check_content_valid(self):
        self.assertTrue(self.correct_problem1.is_content_valid())
        self.assertFalse(self.invalid_content_problem1.is_content_valid())

    def test_state_correctness(self):
        self.assertTrue(self.correct_problem1.is_state_correct())
        self.assertFalse(self.incorrect_problem1.is_state_correct())


class TestBaseSolverClass(unittest.TestCase):

    def setUp(self):

        self.validcodeproblem = Task(
            '''My name is {{username}}.
            I have {{total}} $. I want to buy several papers.
            Each paper worth is {{paper_cost}}$.
            How much papers can I buy?''',
            default_vals={'username': 'Dmitry',
                          'total': 100, 'paper_cost': 20
                          },
            code='''OUTPUTS['result']=int(INPUTS['total']/INPUTS['paper_cost'])'''
        )

        self.notsolvableproblem = Task(
            '''My name is {{username}}. I have {{total}} $.
            I want to buy several papers.
            Each paper worth is {{paper_cost}}$.
            How much papers can I buy?''',
            default_vals={'username': 'Dmitry',
                          'total': 100, 'paper_cost': 20},
            code='''OUTPUTS['result']=INPUTS['total']-/INPUTS['paper_cost']''')

        self.solver = Solver(self.validcodeproblem)
        self.answer = {'result': 5}
        self.async_problems = []
        self.nasynctasks = 200

    def test_solver_creation(self):
        solver = Solver(self.validcodeproblem)
        unsolver = Solver(self.notsolvableproblem)
        self.assertIsNone(solver.total)
        self.assertTrue(solver.is_solvable(silent=False))
        self.assertFalse(unsolver.is_solvable())
        unsolable_rise = False
        try:
            unsolver.solve()
        except UnsolvableProblem:
            unsolable_rise = True
        self.assertTrue(unsolable_rise)

    def test_solver(self):
        self.solver.solve()
        self.assertEqual(self.validcodeproblem.output_vals, self.answer)
        self.assertIsNotNone(self.solver.start)
        self.assertIsNotNone(self.solver.created)
        self.assertIsNotNone(self.solver.end)

    def test_async_solver(self):
        for i in range(self.nasynctasks):
            self.async_problems.append(
                Solver(
                       Task(
                        '''My name is {{username}}.
                    I have {{total}} $. I want to buy several papers.
                   Each paper worth is {{paper_cost}}$.
                    How much papers can I buy?''',
                        default_vals={'username': 'Dmitry', 'total': 100,
                                      'paper_cost': 20},
                        code='''
OUTPUTS['result']=int(INPUTS['total']/INPUTS['paper_cost'])
                        '''),
                       preamble='import time, random'
                       )
                                       )
        for i in range(self.nasynctasks):
            self.async_problems[i].async_solve()
        while not all(map(lambda x: x.is_solved, self.async_problems)):
            pass
        self.solver.async_solve()
        while not self.solver.is_solved:
            pass
        self.assertEqual(self.validcodeproblem.output_vals, self.answer)
        self.assertTrue(self.solver.is_solved)
        print('Average execution time of the task is %s milliseconds' %
              np.mean(list(map(lambda x: x.total, self.async_problems))))


class TestTaskRendererClass(unittest.TestCase):

    def setUp(self):
        self.validcodeproblem = Task(
                '''My name is {{username}}.
                I have ${{total}}. I want to buy several papers.
                Each paper worth is ${{paper_cost}}.
                How much papers can I buy?''',
                default_vals={'username': 'Dmitry', 'total': 100,
                              'paper_cost': 20},
                code='''
OUTPUTS['result']=int(INPUTS['total']/INPUTS['paper_cost'])''',
                solution_template='''Your answer is ${{result}}.'''
                                    )
        self.invalidcodeproblem = Task(
                '''My name is {{username}}.
                I have {{total}} $. I want to buy several papers.
                Each paper worth is ${{paper_cost}}.
                How much papers can I buy?''',
                default_vals={'username': 'Dmitry',
                              'total': 100, 'paper_cost': 20},
                code='''
OUTPUTS['result']=INPUTS['total']/INPUTS['paper_cost']
                ''',
                solution_template='''
                My name is {{name}} and answer is {{result}}.'''
                                        )
        self.invalidtemplateproblem = Task(
            '''My name is {{username}}.
            I have ${{total}}. I want to buy several papers.
            Each paper worth is $ {{paper_cost}}.
            How much papers can I buy?''',
            default_vals={'username': 'Dmitry', 'total': 100,
                          'paper_cost': 20},
            code='''OUTPUTS['result']=INPUTS['total']/INPUTS['paper_cost']''',
            solution_template='''My answer is ${{result}.'''
            )

        self.solver = Solver(self.validcodeproblem)
        self.inv_solver = Solver(self.invalidcodeproblem)
        self.inv_temp = Solver(self.invalidtemplateproblem)

    def test_output_renderer(self):
        self.solver.solve()
        self.inv_solver.solve()
        self.inv_temp.solve()
        self.validcodeproblem.render_outputs()
        self.assertEqual(self.validcodeproblem.output, 'Your answer is $5.')

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.invalidcodeproblem.render_outputs()
            assert issubclass(w[-1].category, SyntaxWarning)
        try:
            self.invalidtemplateproblem.render_outputs()
        except TemplateOutputSyntaxError:
            self.assertTrue(True)


# Simple statistical problem. Quasireal case

quasireal_formulation1 = '''
My task
=======

Initially, I have two samples. One sample is {{sample1}} and the second is {{sample2}}. I need to perform independent t-Student test
for these samples. Null hypotesis is the samples have the same mean values. So, I need to get p-value and t-statistic, and check basic
assumptions for t-test, perviously. Next thing I need to do is performing test for sample normality. If all samples come from normal distribution,
I should make T-student test and print the results. If one sample or both come from non-normal distribution, I should use one of non-parametric tests.
'''
quasireal_default_vals = {'sample1': np.random.randn(100),
                          'sample2': np.random.randn(100)}
quasireal_solution1 = '''
{% if error %}
ERROR
=====

Internal error has rised. Your problem could not be solved (now).
Try to solve it later (when necessary modules will be installed).

System message: 
===============
{{error}}
{% else %}
 You have two samples of sizes {{sample1|length}} and {{sample2|length}}. Null hypotesis for these samples is formulated as follows: means of sample1 and sample2 are equal.
 The following scheme of statistical analysis was performed: 1) tests for normality for two samples; 2) if both samples "come" from normal distribution (hypotesis of normality wasn't rejected), 
 independent Student t-test was applied. 3) if one or both sample come from non-normal distribution, Mann-Whitney U-test was applied. 
 
 {% if p_val_mann %}
    Results of Mann-Whitney U-test:
     p-value is {{p_val_mann}}
     testing code: suejk32kjgsdfsd
 {% elif p_val_classic %}
    Results of independent Student t-test:
    p-value is {{p_val_classic}}
    testing code: htfldkwdjsnak234
 {% endif %}
{% endif %}
'''
quasireal_preamble1 = '''
ERROR=""
try:
    import scipy.stats as st
except ImportError:
    ERROR = "Import Error: Scipy module is not installed."

'''
quasireal_code1 = '''
sample1 = INPUTS['sample1']
sample2 = INPUTS['sample2']

OUTPUTS['error'] = ''
if ERROR:
    OUTPUTS['error'] = ERROR
else:
    OUTPUTS['sample1'] = sample1
    OUTPUTS['sample2'] = sample2
    OUTPUTS['p_val_mann'] = None
    OUTPUTS['p_val_classic'] = None
    if (st.shapiro(sample1)[1]>=0.05) and (st.shapiro(sample2)[1]>=0.05):
        res = st.ttest_ind(sample1, sample2)
        OUTPUTS['p_val_classic'] = res[1]
    else:
        res = st.mannwhitneyu(sample1, sample2)
        OUTPUTS['p_val_mann'] = res[1]

'''


class TestUTtestClass(unittest.TestCase):

    def setUp(self):
        self.ttestproblem = Task(
                            quasireal_formulation1,
                            default_vals=quasireal_default_vals,
                            code=quasireal_code1,
                            solution_template=quasireal_solution1
                                 )
        self.solver = Solver(self.ttestproblem, preamble=quasireal_preamble1)
        quasireal_default_vals1 = {'sample1': np.random.rand(100),
                                   'sample2': np.random.rand(100)}
        self.mannproblem = Task(
                            quasireal_formulation1,
                            default_vals=quasireal_default_vals1,
                            code=quasireal_code1,
                            solution_template=quasireal_solution1
                            )
        self.solverm = Solver(self.mannproblem, preamble=quasireal_preamble1)

    def test_ttest(self):
        self.solver.async_solve()
        while not self.solver.is_solved:
            pass
        self.ttestproblem.render_outputs()
        if self.ttestproblem.output_vals['error']:
            print("SciPy not installed. t-test is aborted.")
        else:
            self.assertIn('htfldkwdjsnak234', self.ttestproblem.output)

    def test_mann(self):
        self.solverm.async_solve()
        while not self.solverm.is_solved:
            pass
        self.mannproblem.render_outputs()
        if self.mannproblem.output_vals['error']:
            print("SciPy not installed. t-test is aborted.")
        else:
            self.assertIn('suejk32kjgsdfsd', self.mannproblem.output)


if __name__ == '__main__':
    unittest.main()
