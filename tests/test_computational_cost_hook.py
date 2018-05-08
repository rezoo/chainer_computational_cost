import chainer
import chainer.functions as F
from chainer.functions.math.basic_math import AddConstant
import chainer.links as L
import numpy as np

import pytest

import chainer_computational_cost


class SimpleConvNet(chainer.Chain):
    def __init__(self):
        super(SimpleConvNet, self).__init__()
        with self.init_scope():
            self.conv1 = L.Convolution2D(None, 32, ksize=3, stride=1, pad=1)
            self.bn1 = L.BatchNormalization(32)
            self.conv2 = L.Convolution2D(None, 32, ksize=3, stride=1, pad=1)
            self.bn2 = L.BatchNormalization(32)
            self.conv3 = L.Convolution2D(None, 32, ksize=3, stride=1, pad=1)
            self.bn3 = L.BatchNormalization(32)
            self.fc4 = L.Linear(None, 100)
            self.fc5 = L.Linear(None, 10)

    def __call__(self, h):
        h = F.relu(self.bn1(self.conv1(h)))
        h = F.relu(self.bn2(self.conv2(h)))
        h = F.relu(self.bn3(self.conv3(h)))
        height, width = h.shape[2:]
        h = F.average_pooling_2d(h, ksize=(height, width))
        h = F.reshape(h, (h.shape[0], -1))
        h = F.relu(self.fc4(h))
        return self.fc5(h)


def test_simple_net():
    x = np.random.randn(1, 3, 32, 32).astype(np.float32)
    net = SimpleConvNet()
    with chainer.using_config('train', False):
        with chainer_computational_cost.ComputationalCostHook():
            net(x)


def test_custom_cost_calculator():
    called = False

    def calc_custom(func: AddConstant, in_data, **kwargs):
        nonlocal called
        called = True
        return (100, 100, 100)

    x = np.random.randn(1, 3, 32, 32).astype(np.float32)
    x = chainer.Variable(x)
    with chainer.using_config('train', False):
        with chainer_computational_cost.ComputationalCostHook() as cost:
            cost.add_custom_cost_calculator(calc_custom)
            x = x + 1
            report = cost.layer_report

    report = report['AddConstant-1']
    assert called is True
    assert report['flops'] == 100
    assert report['mread'] == 100 * x.dtype.itemsize
    assert report['mwrite'] == 100 * x.dtype.itemsize


def test_custom_cost_calculator_invalid():
    def calc_invalid_custom(func, in_data, **kwargs):
        pass

    x = np.random.randn(1, 3, 32, 32).astype(np.float32)
    x = chainer.Variable(x)
    with chainer.using_config('train', False):
        with chainer_computational_cost.ComputationalCostHook() as cost:
            with pytest.raises(TypeError):
                cost.add_custom_cost_calculator(calc_invalid_custom)
                x = x + 1
