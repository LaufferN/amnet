import numpy as np
import amnet

import sys
import unittest
from itertools import chain, product


class TestAtoms(unittest.TestCase):
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

    def test_make_max2(self):
        x = amnet.Variable(2, name='x')
        phi_max2 = amnet.atoms.make_max2(x)

        # true max2
        def max2(x): return x[0] if x[0] > x[1] else x[1]

        # implemented max2
        for xv in self.floatvals:
            for yv in self.floatvals:
                xyv = np.array([xv, yv])
                self.assertEqual(phi_max2.eval(xyv), max2(xyv))

    def test_make_max3(self):
        x = amnet.Variable(3, name='x')
        phi_max3 = amnet.atoms.make_max3(x)

        # true max3
        def max3(x): return np.max(x)

        # implemented max3
        for xv in self.floatvals:
            for yv in self.floatvals:
                for zv in self.floatvals:
                    xyzv = np.array([xv, yv, zv])
                    self.assertEqual(phi_max3.eval(xyzv), max3(xyzv))

    def test_make_max4(self):
        x = amnet.Variable(4, name='x')
        phi_max4 = amnet.atoms.make_max4(x)

        # true max4
        def max4(x): return np.max(x)

        # implemented max4
        for xv, yv, zv, wv in product(self.floatvals2, repeat=4):
            xyzwv = np.array([xv, yv, zv, wv])
            self.assertEqual(phi_max4.eval(xyzwv), max4(xyzwv))

    def test_make_max(self):
        x = amnet.Variable(4, name='x')
        phi_max = amnet.atoms.make_max(x)

        # true max4
        def max_true(x): return np.max(x)

        # implemented max4
        for xv,yv,zv,wv in product(self.floatvals2, repeat=4):
            xyzwv = np.array([xv, yv, zv, wv])
            self.assertEqual(phi_max.eval(xyzwv), max_true(xyzwv))

    def test_make_relu(self):
        x = amnet.Variable(4, name='x')
        y = amnet.Variable(1, name='y')
        phi_relu = amnet.atoms.make_relu(x)
        phi_reluy = amnet.atoms.make_relu(y)

        # true relu
        def relu(x): return np.maximum(x, 0)

        for xv,yv,zv,wv in product(self.floatvals2, repeat=4):
            xyzwv = np.array([xv, yv, zv, wv])
            r = phi_relu.eval(xyzwv) # 4-d relu of x
            s = relu(xyzwv)
            self.assertTrue(len(r) == 4)
            self.assertTrue(len(s) == 4)
            self.assertTrue(all(r == s))

        for yv in self.floatvals:
            r = phi_reluy.eval(np.array([yv])) # 1-d relu of y
            s = relu(np.array([yv]))
            self.assertEqual(r, s)

    def test_make_triplexer(self):
        x = amnet.Variable(1, name='xv')

        np.random.seed(1)

        for iter in range(10):
            a = 3 * (2 * np.random.rand(4) - 1)
            b = 3 * (2 * np.random.rand(4) - 1)
            c = 3 * (2 * np.random.rand(4) - 1)
            d = 3 * (2 * np.random.rand(4) - 1)
            e = 3 * (2 * np.random.rand(4) - 1)
            f = 3 * (2 * np.random.rand(4) - 1)
            phi_tri = amnet.atoms.make_triplexer(x, a, b, c, d, e, f)

            xvals = 100 * (2 * np.random.rand(1000) - 1)
            for xv in xvals:
                self.assertEqual(phi_tri.eval(np.array([xv])),
                                 fp_triplexer(xv, a, b, c, d, e, f))



def fp_mu(x, y, z): return x if z <= 0 else y
def fp_triplexer(inp, a, b, c, d, e, f):
    assert all([len(p) == 4 for p in [a, b, c, d, e, f]])

    x = [0] * 4
    y = [0] * 4
    z = [0] * 4
    w = [0] * 4

    # Layer 1 weights
    for i in range(3):
        x[i] = a[i] * inp + b[i]
        y[i] = c[i] * inp + d[i]
        z[i] = e[i] * inp + f[i]

    # Layer 1 nonlinearity
    for i in range(3):
        w[i] = fp_mu(x[i], y[i], z[i])

    # Layer 2 weights
    x[3] = a[3] * w[1] + b[3]
    y[3] = c[3] * w[2] + d[3]
    z[3] = e[3] * w[0] + f[3]

    # Layer 2 nonlinearity
    w[3] = fp_mu(x[3], y[3], z[3])

    return w[3]

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAtoms)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
