# Exception definitions


class AbstractSolverException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class AbstractTaskExcpetion(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class AbstractRenderException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class InappropriateSolverTypeError(AbstractSolverException):
    '''Should raised when we use not Solver instances
    for a problem solution.
    '''
    pass


class UnsolvableProblem(AbstractSolverException):
    def __init__(self):
        self.msg = "Could not parse your code block. Check it for correctness."


class TemplateOutputSyntaxError(AbstractRenderException):
    '''Raised if output template includes syntax errors'''
    pass


class OutputValuesError(AbstractRenderException):
    '''Raised when not all values are defined for output rendering.'''
#    TODO:
#    Probably should be removed. Not used.
    pass
