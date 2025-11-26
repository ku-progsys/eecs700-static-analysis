class IntervalDomain:
    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    @classmethod
    def bottom(cls):
        return cls(1, 0)

    @classmethod
    def top(cls):
        return cls(float('-inf'), float('inf'))

    def is_bottom(self):
        return self.lower > self.upper
    
    def is_top(self):
        return self.lower == float('-inf') and self.upper == float('inf')

    def __repr__(self):
        return f"[{self.lower}, {self.upper}]"

    def join(self, other):
        return IntervalDomain(min(self.lower, other.lower), max(self.upper, other.upper))

    def widen(self, other):
        new_lower = self.lower if other.lower >= self.lower else float('-inf')
        new_upper = self.upper if other.upper <= self.upper else float('inf')
        return IntervalDomain(new_lower, new_upper)

    def __add__(self, other):
        return IntervalDomain(self.lower + other.lower, self.upper + other.upper)

    def __sub__(self, other):
        return IntervalDomain(self.lower - other.upper, self.upper - other.lower)

    def __mul__(self, other):
        candidates = [self.lower * other.lower, self.lower * other.upper,
                      self.upper * other.lower, self.upper * other.upper]
        return IntervalDomain(min(candidates), max(candidates))

    def __le__(self, other):
        return self.lower >= other.lower and self.upper <= other.upper


class ZeroNonZeroDomain:
    def __init__(self, val):
        self.val = val

    @classmethod
    def bottom(cls):
        return cls('bot')

    @classmethod
    def top(cls):
        return cls('top')

    def is_bottom(self):
        return self.val == 'bot'
    
    def is_top(self):
        return self.val == 'top'

    def __repr__(self):
        return f"{self.val}"

    def join(self, other):
        if self.is_bottom() and other.is_bottom():
            return ZeroNonZeroDomain.bottom()
        elif self.is_bottom() and not other.is_bottom():
            return ZeroNonZeroDomain(other.val)
        elif not self.is_bottom() and other.is_bottom():
            return ZeroNonZeroDomain(self.val)
        elif self.val == other.val:
            return ZeroNonZeroDomain(self.val)
        else:
            return ZeroNonZeroDomain.top()

    def widen(self, other):
        new_val = 'top' if other.val == 'top' else self.val
        return ZeroNonZeroDomain(new_val)

    def __add__(self, other):
        if self.is_bottom() or other.is_bottom():
            return ZeroNonZeroDomain.bottom()
        if self.is_top() or other.is_top():
            return ZeroNonZeroDomain.top()
        if self.val == 'zero' and other.val == 'zero':
            return ZeroNonZeroDomain('zero')
        else:
            return ZeroNonZeroDomain('nonzero')
    
    def __sub__(self, other):
        if self.is_bottom() or other.is_bottom():
            return ZeroNonZeroDomain.bottom()
        if self.is_top() or other.is_top():
            return ZeroNonZeroDomain.top()
        if self.val == 'zero' and other.val == 'zero':
            return ZeroNonZeroDomain('zero')
        else:
            return ZeroNonZeroDomain('nonzero')

    def __le__(self, other):
        if self.is_bottom():
            return True
        if other.is_top():
            return True
        return self.val == other.val


def join_env(env1, env2):
    keys = set(env1.keys()).union(set(env2.keys()))
    new_env = {}
    for k in keys:
        v1 = env1.get(k, ZeroNonZeroDomain.bottom())
        v2 = env2.get(k, ZeroNonZeroDomain.bottom())
        new_env[k] = v1.join(v2)
    return new_env

def leq_env(env1, env2):
    keys = set(env1.keys()).union(set(env2.keys()))
    for k in keys:
        v1 = env1.get(k, ZeroNonZeroDomain.bottom())
        v2 = env2.get(k, ZeroNonZeroDomain.bottom())
        if not (v1 <= v2):
            return False
    return True



def abs_zero_nonzero_domain(value):
    if value == 0:
        return ZeroNonZeroDomain('zero')
    else:
        return ZeroNonZeroDomain('nonzero')







# this function does the abstract interpretation using interval domain
# using the kildall fixpoint algorithm
def absint(stmt, env):
    if stmt[0] == 'skip':
        return env

    elif stmt[0] == 'assign':
        var = stmt[1]
        expr = stmt[2]
        value = eval_expr(expr, env)
        new_env = env.copy()
        new_env[var] = value
        return new_env

    elif stmt[0] == 'seq':
        for s in stmt[1:]:
            env = absint(s, env)
        return env




    elif stmt[0] == 'if':
        cond = stmt[1]
        then_branch = stmt[2]
        else_branch = stmt[3]

        then_env = absint(['seq'] + then_branch, env)
        else_env = absint(['seq'] + else_branch, env)

        return join_env(then_env, else_env)








    elif stmt[0] == 'while':
        cond = stmt[1]
        body = stmt[2]
        # no invariants are provided
        # use a simple fixpoint iteration with widening after k iterations
        max_iterations = 10
        iteration = 0
        prev_env = {k: ZeroNonZeroDomain.bottom() for k in env.keys()}
        current_env = env.copy()
        while True:
            iteration += 1
            body_env = absint(['seq'] + body, current_env)
            new_env = join_env(env, body_env)
            if leq_env(new_env, current_env):
                break # reached a fixpoint
            if iteration >= max_iterations:
                new_env = {k: current_env[k].widen(new_env[k]) for k in new_env.keys()}
            current_env = new_env
        return current_env

    else:
        raise NotImplementedError(stmt)


def eval_expr(expr, env):
    if expr[0] == 'const':
        return abs_zero_nonzero_domain(expr[1])
    elif expr[0] == 'var':
        return env.get(expr[1], ZeroNonZeroDomain.top())
    elif expr[0] == '+':
        return eval_expr(expr[1], env) + eval_expr(expr[2], env)
    elif expr[0] == '-':
        return eval_expr(expr[1], env) - eval_expr(expr[2], env)
    elif expr[0] == '*':
        return eval_expr(expr[1], env) * eval_expr(expr[2], env)
    else:
        return ZeroNonZeroDomain.top()

if __name__ == "__main__":
    from parser import py_ast, WhilePyVisitor
    import sys
    filename = sys.argv[1]
    tree = py_ast(filename)
    visitor = WhilePyVisitor()
    stmt = visitor.visit(tree)
    print("Program AST:", stmt)
    initial_env = {}
    final_env = absint(stmt, initial_env)
    print(f"Final Abstract Environment: {final_env}")
