import amnet
import z3


class SmtEncoder(object):
    def __init__(self, phi):
        self.symbols = dict()  # name str -> z3 variable
        self.phi = phi

    def next_unique_varname(self, prefix='x'):
        assert len(prefix) >= 1
        assert prefix[0].isalpha()

        # all variables already used, with the given prefix
        existing = filter(lambda x: x.startswith(prefix),
                          self.symbols.keys())

        # find a unique suffix
        if len(existing) == 0:
            return prefix + '0'

        # TODO: can be more efficient by keeping track of max suffix state
        max_suffix = max(int(varname[len(prefix):]) for varname in existing)
        return prefix + str(max_suffix + 1)

    def add_new_symbol(self, name, target=None):
        assert name not in self.symbols
        self.symbols[name] = target

    def add_new_var(self, name, dim=1):
        assert dim >= 1

        self.add_new_symbol(name)
        if dim == 1:
            self.symbols[name] = z3.Real(name)
        else:
            self.symbols[name] = z3.RealVector(name, dim)
