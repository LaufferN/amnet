import numpy as np
import amnet

import z3

import sys
import unittest
import itertools

class TestSmt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print 'Setting up test floats.'
        cls.floatvals = np.concatenate(
            (np.linspace(-5., 5., 11), np.linspace(-5., 5., 10)),
            axis=0
        )
        cls.floatvals2 = np.concatenate(
            (np.linspace(-5., 5., 3), np.linspace(-.5, .5, 2)),
            axis=0
        )

    def test_SmtEncoder(self):
        xyz = amnet.Variable(3, name='xyz')

        x = amnet.select(xyz, 0)
        y = amnet.select(xyz, 1)
        z = amnet.select(xyz, 2)
        w = amnet.Mu(x, y, z)

        enc = amnet.smt.SmtEncoder(w)

        # check naming
        name0 = enc.get_unique_varname(prefix='x')
        self.assertEqual(name0, 'x0')
        enc.add_new_symbol(name0)

        name1 = enc.get_unique_varname(prefix='x')
        self.assertEqual(name1, 'x1')
        enc.add_new_symbol(name1)

        name2 = enc.get_unique_varname(prefix='y')
        self.assertEqual(name2, 'y0')
        enc.add_new_symbol(name2)

        name3 = enc.get_unique_varname(prefix='y')
        self.assertEqual(name3, 'y1')
        enc.add_new_symbol(name3)

        # clear symbols
        enc.symbols = dict()
        enc.solver = z3.Solver()

        # now add some variables
        name = enc.get_unique_varname(prefix='x')
        enc.add_new_var(name)

        name = enc.get_unique_varname(prefix='x')
        enc.add_new_var(name, 2)

        self.assertTrue('x0' in enc.symbols)
        self.assertEqual(len(enc.symbols['x0']), 1)

        self.assertTrue('x1' in enc.symbols)
        self.assertEqual(len(enc.symbols['x1']), 2)

    def test_SmtEncoder2(self):
        xyz = amnet.Variable(3, name='xyz')

        x = amnet.select(xyz, 0)
        y = amnet.select(xyz, 1)
        z = amnet.select(xyz, 2)
        w = amnet.Mu(x, y, z)

        # do the smt encoding
        enc = amnet.smt.SmtEncoder(w)
        enc.init_tree()

        self.assertTrue(enc.solver.check())

        # bind the variables to an input
        enc.set_const(xyz, np.array([1, 2, 3]))
        self.assertTrue(enc.solver.check())
        model = enc.solver.model()

        #print model

        out_z3_list = enc.symbols[w.outvar]
        out_z3_val = model[out_z3_list[0]]
        self.assertEqual(out_z3_val, 2)

    def test_SmtEncoder3(self):
        xyz = amnet.Variable(3, name='xyz')

        x = amnet.select(xyz, 0)
        y = amnet.select(xyz, 1)
        z = amnet.select(xyz, 2)
        w = amnet.Mu(x, y, z)

        # do the smt encoding
        enc = amnet.smt.SmtEncoder(w)
        enc.init_tree()

        self.assertTrue(enc.solver.check())

        # bind the variables to an input
        enc.set_const(xyz, np.array([1, 2, -3.1]))
        self.assertTrue(enc.solver.check())
        model = enc.solver.model()

        # print model

        out_z3_list = enc.symbols[w.outvar]
        out_z3_val = model[out_z3_list[0]]
        self.assertEqual(out_z3_val, 1)

    def test_SmtEncoder3(self):
        xyz = amnet.Variable(3, name='xyz')

        x = amnet.select(xyz, 0)
        y = amnet.select(xyz, 1)
        z = amnet.select(xyz, 2)
        w = amnet.Mu(x, y, z)

        # do the smt encoding
        enc = amnet.smt.SmtEncoder(w)
        enc.init_tree()

        self.assertTrue(enc.solver.check())

        # bind the variables to an input
        enc.set_const(xyz, np.array([1.2, 2, -3.1]))
        self.assertTrue(enc.solver.check())
        model = enc.solver.model()

        # retrieve the output
        wsym = enc.get_symbol(w)
        self.assertEqual(len(wsym), 1)
        wval = model[wsym[0]]

        self.assertEqual(wval, 1.2)

    def test_SmtEncoder_Mutest(self):
        xyz = amnet.Variable(3, name='xyzv')

        x = amnet.select(xyz, 0)
        y = amnet.select(xyz, 1)
        z = amnet.select(xyz, 2)
        w = amnet.Mu(x, y, z)

        # do the smt encoding
        enc = amnet.smt.SmtEncoder(w)
        enc.init_tree()
        wsym = enc.get_symbol(w)

        def true_mu(x, y, z): return x if z <= 0 else y

        # set the output
        for xv, yv, zv in itertools.product(self.floatvals2, repeat=3):
            enc.solver.push()

            enc.set_const(xyz, np.array([xv, yv, zv]))
            self.assertTrue(enc.solver.check())

            model = enc.solver.model()
            wval = model[wsym[0]]
            self.assertEqual(wval, true_mu(xv, yv, zv))

            enc.solver.pop()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSmt)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
