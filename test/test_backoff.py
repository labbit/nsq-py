import mock
import unittest

from nsq import backoff


class TestBackoff(unittest.TestCase):
    '''Test our backoff class'''
    def setUp(self):
        self.backoff = backoff.Backoff()

    def test_sleep(self):
        '''Just calls time.sleep with whatever backoff returns'''
        with mock.patch.object(self.backoff, 'backoff', return_value=5):
            with mock.patch('nsq.backoff.time') as MockTime:
                self.backoff.sleep(10)
                self.backoff.backoff.assert_called_with(10)
                MockTime.sleep.assert_called_with(5)

    def test_backoff(self):
        '''Not implemented on the base class'''
        self.assertRaises(NotImplementedError, self.backoff.backoff, 1)


class TestLinear(unittest.TestCase):
    '''Test our linear backoff class'''
    def setUp(self):
        self.backoff = backoff.Linear(1, 2)

    def test_constant(self):
        '''The constant is added to each time'''
        self.assertEqual(self.backoff.backoff(0), 2)

    def test_affine(self):
        '''The affine factor works as advertised'''
        self.assertEqual(self.backoff.backoff(0) + 1, self.backoff.backoff(1))


class TestConstant(unittest.TestCase):
    '''Test our constant backoff class'''
    def setUp(self):
        self.backoff = backoff.Constant(10)

    def test_constant(self):
        '''Always gives the same result'''
        for i in xrange(100):
            self.assertEqual(self.backoff.backoff(0), self.backoff.backoff(i))


class TestExponential(unittest.TestCase):
    '''Test our exponential backoff class'''
    def test_factor(self):
        '''We make use of the constant factor'''
        base = 5
        one = backoff.Exponential(base, 1)
        two = backoff.Exponential(base, 2)
        for i in xrange(10):
            self.assertEqual(one.backoff(i) * 2, two.backoff(i))

    def test_constant(self):
        '''We add the constant value'''
        base = 5
        four = backoff.Exponential(base, c=4)
        zero = backoff.Exponential(base)
        for i in xrange(10):
            self.assertEqual(zero.backoff(i) + 4, four.backoff(i))

    def test_base(self):
        '''We honor the base'''
        one = backoff.Exponential(1)
        two = backoff.Exponential(2)
        self.assertEqual(one.backoff(1) * 2, two.backoff(1))
        self.assertEqual(one.backoff(2) * 4, two.backoff(2))


class TestAttemptCounter(unittest.TestCase):
    '''Test the attempt counter'''
    def setUp(self):
        self.backoff = mock.Mock()
        self.counter = backoff.AttemptCounter(self.backoff)

    def test_sleep(self):
        '''Just calls time.sleep with whatever backoff returns'''
        with mock.patch.object(self.counter, 'backoff', return_value=5):
            with mock.patch('nsq.backoff.time') as MockTime:
                self.counter.sleep()
                self.counter.backoff.assert_called_with()
                MockTime.sleep.assert_called_with(5)

    def test_backoff(self):
        '''Not implemented on the base class'''
        with mock.patch.object(self.counter, 'attempts', 5):
            self.assertEqual(
                self.counter.backoff(), self.backoff.backoff.return_value)
            self.backoff.backoff.assert_called_with(5)

    def test_success(self):
        '''Success not implemented on the base class'''
        self.assertRaises(NotImplementedError, self.counter.success)

    def test_failed(self):
        '''Failed increments the number of attempts'''
        for attempts in range(10):
            self.assertEqual(self.counter.attempts, attempts)
            self.counter.failed()


class TestResettingAttemptCounter(unittest.TestCase):
    '''Test the ResettingAttemptCounter'''
    def setUp(self):
        self.counter = backoff.ResettingAttemptCounter(None)

    def test_success(self):
        '''Success resets the attempts counter'''
        for _ in range(10):
            self.counter.failed()
        self.counter.success()
        self.assertEqual(self.counter.attempts, 0)


class TestDecrementingAttemptCounter(unittest.TestCase):
    def setUp(self):
        self.counter = backoff.DecrementingAttemptCounter(None)

    def test_success(self):
        '''Success only decrements the attempts counter'''
        for _ in range(10):
            self.counter.failed()
        self.counter.success()
        self.assertEqual(self.counter.attempts, 9)

    def test_negative_attempts(self):
        '''Success never lets the attempts count drop below 0'''
        self.counter.success()
        self.assertEqual(self.counter.attempts, 0)
