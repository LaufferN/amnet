import amnet
import z3
from itertools import izip, chain


class NamingContext(object):
    """
    NamingContext keeps track of a mapping (symbol table)
    symbols[name -> node]
    """
    @classmethod
    def default_prefix_for(cls, phi):
        """
        Returns a string that is an appropriate prefix for 
        the amn node type of phi
        """
        # the checking order should go *up* the class hierarchy
        if isinstance(phi, amnet.Variable):
            return 'var'
        elif isinstance(phi, amnet.Linear):
            return 'lin'
        elif isinstance(phi, amnet.Constant):
            return 'con'
        elif isinstance(phi, amnet.Affine):
            return 'aff'
        elif isinstance(phi, amnet.Mu):
            return 'mu'
        elif isinstance(phi, amnet.Stack):
            return 'st'
        elif isinstance(phi, amnet.Amn):
            return 'amn'
        else:
            assert False

    def is_valid(self):
        """
        Checks that the symbol table has a valid inverse
        by verifying that symbols is an bijection
        (no two names map to the same node, and there are no null pointers)
        """

        # ensure surjectivity
        for _, v in self.symbols.items():
            if v is None:
                return False

        # ensure injectivity
        ids = set(id(v) for v in self.symbols.values())
        return len(ids) == len(self.symbols.values())


    def __init__(self, root=None):
        self.symbols = dict()

        # does not touch the tree, only assigns to it
        if root is not None:
            self.assign_names(root)

    def prefix_names(self, prefix):
        """
        Get all existing names for a given prefix
        """
        # all names beginning with the given prefix
        return [name
                for name in self.symbols.keys()
                if name.startswith(prefix)]

    def next_unique_name(self, prefix):
        """
        Generate a unique name for a given prefix 
        """
        # if there are no existing variables return new varname
        pnames = self.prefix_names(prefix)
        if len(pnames) == 0:
            retval = prefix + '0'
            assert retval not in self.symbols, 'bad prefix'
            return retval

        # otherwise, return 1 + largest value in the names
        #pnums = [int(name[len(prefix):]) for name in pnames]
        #maxnum = max(pnums)
        pnums = []
        for name in pnames:
            suffix = name[len(prefix):]
            if suffix.isdigit():
                pnums.append(int(suffix))
        if len(pnums) == 0:
            retval = prefix + '0'
            assert retval not in self.symbols, 'bad prefix'
            return retval
        maxnum = max(pnums)

        retval = prefix + str(1 + maxnum)
        assert retval not in self.symbols, 'bad prefix'
        return retval

    def name_of(self, phi):
        """
        Returns the name of Amn phi, or None if it 
        does not exist in the naming context
        """
        for k, v in self.symbols.items():
            if v is phi:
                return k

        return None

    def assign_name(self, phi):
        """
        Assigns a name to phi (and only phi), 
        provided it does not already have a name
        in the naming context
        """
        visited = (self.name_of(phi) is not None)

        if not visited:
            # get a unique name
            name = self.next_unique_name(prefix=NamingContext.default_prefix_for(phi))

            # assign the name
            self.symbols[name] = phi

        return visited

    def assign_names(self, phi):
        """
        Recursively walks the tree for phi,
        and assigns a name to each node
        """
        visited = self.assign_name(phi)

        if visited:
            #print 'Found a previously visited node (%s)' % self.name_of(phi),
            return

        if hasattr(phi, 'x'):
            self.assign_names(phi.x)
        if hasattr(phi, 'y'):
            assert isinstance(phi, amnet.Mu) or \
                   isinstance(phi, amnet.Stack)
            self.assign_names(phi.y)
        if hasattr(phi, 'z'):
            assert isinstance(phi, amnet.Mu)
            self.assign_names(phi.z)

    def signal_graph(self):
        """
        Returns a dictionary with 
        keys = names of the nodes in the naming context
        values = names of the children of the nodes
        """
        sg = dict()
        for name, phi in self.symbols.items():
            if name not in sg:
                sg[name] = list()
            if hasattr(phi, 'x'):
                sg[name].append(self.name_of(phi.x))
            if hasattr(phi, 'y'):
                sg[name].append(self.name_of(phi.y))
            if hasattr(phi, 'z'):
                sg[name].append(self.name_of(phi.z))

        return sg

    def rename(self, phi, newname):
        oldname = self.name_of(phi)
        assert oldname is not None, 'nothing to rename'
        assert newname and newname[0].isalpha(), 'invalid new name'

        # maintain invariant
        assert self.is_valid()

        # if newname already exists, rename that variable first
        if newname in self.symbols:
            phi2 = self.symbols[newname]
            name2 = self.next_unique_name(
                prefix=NamingContext.default_prefix_for(phi2)
            )
            print 'Warning (rename): %s exists within context, moving existing symbol to %s' % \
                  (newname, name2)
            self.symbols[name2] = phi2

        # now simply reattach the object
        self.symbols[newname] = self.symbols[oldname]
        del self.symbols[oldname]

        # maintain invariant
        assert self.is_valid()

    def merge_ctx(self, other_ctx):
        """
        Merges another naming context into the current context, keeping the
        same names if possible. 
        Renames the symbols from the other context when necessary.
        """
        assert self.is_valid()

        # for asserts
        nodes_premerge = len(self.symbols)
        nodes_added = 0

        for other_name, other_phi in other_ctx.symbols.items():
            here_name = self.name_of(other_phi)
            if here_name is None:
                # other node is not in current ctx,
                # try to keep the same name
                if other_name not in self.symbols:
                    self.symbols[other_name] = other_phi
                else:
                    other_name2 = self.next_unique_name(
                        prefix=NamingContext.default_prefix_for(other_phi)
                    )
                    self.symbols[other_name2] = other_phi

                nodes_added += 1
            else:
                # node already in current context, keep it
                print 'Warning (merge): %s already in destination context as %s' % \
                      (k, vname)

        # keep invariant
        nodes_postmerge = len(self.symbols)
        assert nodes_postmerge == nodes_premerge + nodes_added
        assert self.is_valid()


class SmtEncoder(object):
    def __init__(self, phi, solver=None):
        self.symbols = dict()  # name str -> z3 variable
        self.phi = phi
        if solver is None:
            self.solver = z3.Solver()
        else:
            self.solver = solver

    def __str__(self):
        return 'SmtEncoder: ' + str(self.symbols)

    def get_unique_varname(self, prefix='x'):
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
        self.add_new_symbol(name, z3.RealVector(name, dim))

    def get_symbol(self, psi):
        return self.symbols[psi.outvar]

    def set_symbol(self, psi, target):
        self.symbols[psi.outvar] = target

    # helper methods for adding variables to each element type
    def _get_unique_outvarname(self, psi):
        if isinstance(psi, amnet.Variable):
            #return self.get_unique_varname(prefix='xv')
            return self.get_unique_varname(prefix=psi.name)
        elif isinstance(psi, amnet.Affine):
            return self.get_unique_varname(prefix='ya')
        elif isinstance(psi, amnet.Mu):
            return self.get_unique_varname(prefix='wm')
        elif isinstance(psi, amnet.Constant):
            return self.get_unique_varname(prefix='c')
        elif isinstance(psi, amnet.Stack):
            return self.get_unique_varname(prefix='xys'),
        else:
            return self.get_unique_varname(prefix='aa')

    def _init_outvar(self, psi):
        """ only touches the specific node in the tree """
        if not hasattr(psi, 'outvar'):
            psi.outvar = self._get_unique_outvarname(psi)
            self.add_new_var(psi.outvar, psi.outdim)

        psi.enc = self

        assert len(self.symbols[psi.outvar]) == psi.outdim

    def _init_tree(self, psi):
        """ touches the whole tree """
        # 1. initialize the output variable
        self._init_outvar(psi)

        # 2. bind to the inputs by adding a constraint
        if isinstance(psi, amnet.Variable):
            # do not bind the input of a variable
            pass
        elif isinstance(psi, amnet.Affine):
            self._init_tree(psi.x)

            xv = self.symbols[psi.x.outvar]
            yv = self.symbols[psi.outvar]

            assert len(yv) == psi.outdim
            assert len(xv) >= 1

            for i in range(psi.outdim):
                rowi = psi.w[i,:]
                bi = psi.b[i]

                rowsum = z3.Sum([wij * xj for wij, xj in izip(rowi, xv) if wij != 0])
                #rowsum = z3.Sum([wij * xj for wij, xj in izip(rowi, xv)])
                if bi == 0:
                    self.solver.add(yv[i] == rowsum)
                else:
                    self.solver.add(yv[i] == rowsum + bi)

        elif isinstance(psi, amnet.Mu):
            self._init_tree(psi.x)
            self._init_tree(psi.y)
            self._init_tree(psi.z)

            xv = self.symbols[psi.x.outvar]
            yv = self.symbols[psi.y.outvar]
            zv = self.symbols[psi.z.outvar]
            wv = self.symbols[psi.outvar]

            assert len(zv) == 1
            assert len(xv) == len(yv)
            assert len(xv) == psi.outdim
            assert len(wv) == len(xv)

            z = zv[0]
            for i in range(len(wv)):
                x, y, = xv[i], yv[i]
                w = wv[i]
                self.solver.add(w == z3.If(z <= 0, x, y))

        elif isinstance(psi, amnet.Constant):
            # convert z3 variable ('RealVec') to a z3 constant (list of 'RealVal')
            # and bind it to the constant value
            self.symbols[psi.outvar] = [z3.RealVal(ci) for ci in psi.c]
        elif isinstance(psi, amnet.Stack):
            print 'Init stack: ' + str(psi.outvar)
            print 'S1 = ' + str(psi.x)
            print 'S2 = ' + str(psi.y)
            self._init_tree(psi.x)
            self._init_tree(psi.y)

            xv = self.symbols[psi.x.outvar]
            yv = self.symbols[psi.y.outvar]
            xyv = self.symbols[psi.outvar]

            assert len(xv) + len(yv) == len(xyv)

            for left, right in izip(xyv, chain(xv, yv)):
                self.solver.add(left == right)
        else:
            raise Exception('Invalid node type')

    def init_tree(self):
        self._init_tree(self.phi)

    def set_const(self, psi, c):
        """ set output of amn psi to numpy array c """
        yv = self.get_symbol(psi)

        assert len(yv) == len(c)

        for yvi, ci in izip(yv, c):
            self.solver.add(yvi == z3.RealVal(ci))
