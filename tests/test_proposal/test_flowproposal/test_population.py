# -*- coding: utf-8 -*-
"""Test methods related to popluation of the proposal after training"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, call

from nessai.proposal import FlowProposal
from nessai.livepoint import numpy_array_to_live_points


@pytest.fixture()
def z():
    return np.random.randn(2, 2)


@pytest.fixture()
def x(z):
    return numpy_array_to_live_points(np.random.randn(*z.shape), ['x', 'y'])


@pytest.fixture()
def log_q(x):
    return np.random.randn(x.size)


def test_log_prior_wo_reparameterisation(proposal, x):
    """Test the lop prior method"""
    log_prior = -np.ones(x.size)
    proposal._reparameterisation = None
    proposal.model = MagicMock()
    proposal.model.log_prior = MagicMock(return_value=log_prior)

    log_prior_out = FlowProposal.log_prior(proposal, x)

    assert np.array_equal(log_prior, log_prior_out)
    proposal.model.log_prior.assert_called_once_with(x)


def test_log_prior_w_reparameterisation(proposal, x):
    """Test the lop prior method with reparameterisations"""
    log_prior = -np.ones(x.size)
    proposal._reparameterisation = MagicMock()
    proposal._reparameterisation.log_prior = MagicMock(return_value=log_prior)
    proposal.model = MagicMock()
    proposal.model.log_prior = MagicMock(return_value=log_prior)

    log_prior_out = FlowProposal.log_prior(proposal, x)

    assert np.array_equal(log_prior_out, -2 * np.ones(x.size))
    proposal._reparameterisation.log_prior.assert_called_once_with(x)
    proposal.model.log_prior.assert_called_once_with(x)


@pytest.mark.parametrize('acceptance, scale',
                         [(0.0, 10.0), (0.5, 2.0), (0.01, 10.0), (2.0, 1.0)])
def test_update_poolsize_scale(proposal, acceptance, scale):
    """Test the check the poolsize is correct adjusted based on the acceptance.
    """
    proposal.max_poolsize_scale = 10.
    FlowProposal.update_poolsize_scale(proposal, acceptance)
    assert proposal._poolsize_scale == scale


def test_compute_weights(proposal, x, log_q):
    """Test method for computing rejection sampling weights"""
    proposal.use_x_prime_prior = False
    proposal.log_prior = MagicMock(return_value=-np.ones(x.size))
    log_w = FlowProposal.compute_weights(proposal, x, log_q)

    proposal.log_prior.assert_called_once_with(x)
    out = (-1 - log_q)
    out -= out.max()
    assert np.array_equal(log_w, out)


def test_compute_weights_prime_prior(proposal, x, log_q):
    """Test method for computing rejection sampling weights with the prime
    prior.
    """
    proposal.use_x_prime_prior = True
    proposal.x_prime_log_prior = MagicMock(return_value=-np.ones(x.size))
    log_w = FlowProposal.compute_weights(proposal, x, log_q)

    proposal.x_prime_log_prior.assert_called_once_with(x)
    out = (-1 - log_q)
    out -= out.max()
    assert np.array_equal(log_w, out)


@patch('numpy.random.rand', return_value=np.array([0.1, 0.9]))
def test_rejection_sampling(proposal, z, x, log_q):
    """Test rejection sampling method."""
    proposal.use_x_prime_prior = False
    proposal.truncate = False
    proposal.backward_pass = MagicMock(return_value=(x, log_q))
    log_w = np.log(np.array([0.5, 0.5]))
    proposal.compute_weights = MagicMock(return_value=log_w)

    z_out, x_out = FlowProposal.rejection_sampling(proposal, z)

    assert proposal.backward_pass.called_once_with(x, True)
    assert proposal.compute_weights.called_once_with(x)
    assert x_out.size == 1
    assert z_out.shape == (1, 2)
    assert np.array_equal(x_out[0], x[0])
    assert np.array_equal(z_out[0], z[0])


def test_rejection_sampling_empty(proposal, z):
    """Test rejection sampling method if no valid points are produced by
    `backwards_pass`
    """
    proposal.use_x_prime_prior = False
    proposal.truncate = False
    proposal.backward_pass = \
        MagicMock(return_value=(np.array([]), np.array([])))

    z_out, x_out = FlowProposal.rejection_sampling(proposal, z)

    assert x_out.size == 0
    assert z_out.size == 0


@patch('numpy.random.rand', return_value=np.array([0.1]))
def test_rejection_sampling_truncate(proposal, z, x):
    """Test rejection sampling method with truncation"""
    proposal.use_x_prime_prior = False
    proposal.truncate = True
    log_q = np.array([0.0, 1.0])
    proposal.backward_pass = MagicMock(return_value=(x, log_q))
    worst_q = 0.5
    log_w = np.log(np.array([0.5]))
    proposal.compute_weights = MagicMock(return_value=log_w)

    z_out, x_out = \
        FlowProposal.rejection_sampling(proposal, z, worst_q=worst_q)

    assert proposal.backward_pass.called_once_with(x, True)
    assert proposal.compute_weights.called_once_with(x)
    assert x_out.size == 1
    assert z_out.shape == (1, 2)
    assert np.array_equal(x_out[0], x[1])
    assert np.array_equal(z_out[0], z[1])


def test_rejection_sampling_truncate_missing_q(proposal, z, x, log_q):
    """Test rejection sampling method with truncation without without q"""
    proposal.use_x_prime_prior = False
    proposal.truncate = True
    log_q = np.array([0.0, 1.0])
    proposal.backward_pass = MagicMock(return_value=(x, log_q))

    with pytest.raises(RuntimeError) as excinfo:
        FlowProposal.rejection_sampling(proposal, z, worst_q=None)
    assert 'Cannot use truncation' in str(excinfo.value)


def test_compute_acceptance(proposal):
    """Test the compute_acceptance method"""
    proposal.samples = np.arange(1, 11, dtype=float).view([('logL', 'f8')])
    acc = FlowProposal.compute_acceptance(proposal, 5.0)
    assert acc == 0.5


def test_convert_to_samples(proposal):
    """Test covert to sample without the prime prior"""
    samples = numpy_array_to_live_points(np.random.randn(10, 4), ['x', 'y'])
    proposal.use_x_prime_prior = False
    proposal.model = MagicMock()
    proposal.model.names = ['x']
    proposal.model.log_prior = MagicMock(return_value=np.ones(10))

    out_samples = FlowProposal.convert_to_samples(proposal, samples, plot=True)

    assert out_samples.dtype.names == ('x', 'logP', 'logL')


@patch('nessai.proposal.flowproposal.plot_1d_comparison')
def test_convert_to_samples_with_prime(mock_plot, proposal):
    """Test covert to sample with the prime prior"""
    samples = numpy_array_to_live_points(np.random.randn(10, 4), ['x', 'y'])
    proposal.use_x_prime_prior = True
    proposal.model = MagicMock()
    proposal.model.names = ['x']
    proposal.model.log_prior = MagicMock(return_value=np.ones(10))
    proposal._plot_pool = True
    proposal.training_data_prime = 'data'
    proposal.output = './'
    proposal.populated_count = 1
    proposal.inverse_rescale = MagicMock(return_value=(samples, None))

    out_samples = FlowProposal.convert_to_samples(proposal, samples, plot=True)

    mock_plot.assert_called_once_with(
        'data', samples, labels=['live points', 'pool'],
        filename='.//pool_prime_1.png')
    proposal.inverse_rescale.assert_called_once()
    assert out_samples.dtype.names == ('x', 'logP', 'logL')


def test_populate(proposal):
    """Test the main populate method"""
    n_dims = 2
    poolsize = 10
    drawsize = 5
    names = ['x', 'y']
    worst_point = np.array([1, 2])
    worst_z = np.random.randn(1, n_dims)
    worst_q = np.random.randn(1)
    z = [
        np.random.randn(drawsize, n_dims),
        np.random.randn(drawsize, n_dims),
        np.random.randn(drawsize, n_dims)
    ]
    x = [
        numpy_array_to_live_points(np.random.randn(drawsize, n_dims), names),
        numpy_array_to_live_points(np.random.randn(drawsize, n_dims), names),
        numpy_array_to_live_points(np.random.randn(drawsize, n_dims), names),
    ]

    proposal.max_radius = 50
    proposal.dims = n_dims
    proposal.poolsize = poolsize
    proposal.drawsize = drawsize
    proposal.min_radius = 0.1
    proposal.fuzz = 1.0
    proposal.indices = []
    proposal.keep_samples = False
    proposal.fixed_radius = False
    proposal.compute_radius_with_all = False
    proposal.check_acceptance = False
    proposal._plot_pool = True
    proposal.populated_count = 1
    proposal.population_dtype = \
        [('x_prime', 'f8'), ('y_prime', 'f8'), ('logP', 'f8'), ('logL', 'f8')]
    proposal.draw_latent_kwargs = {'var': 2.0}

    proposal.forward_pass = MagicMock(return_value=(worst_z, worst_q))
    proposal.radius = MagicMock(return_value=(1.0, worst_q))
    proposal.get_alt_distribution = MagicMock(return_value=None)
    proposal.draw_latent_prior = MagicMock(side_effect=z)
    proposal.rejection_sampling = MagicMock(
        side_effect=[(a[:-1], b[:-1]) for a, b in zip(z, x)]
    )

    proposal.plot_pool = MagicMock()
    proposal.convert_to_samples = MagicMock(
        side_effect=lambda *args, **kwargs: args[0]
    )

    FlowProposal.populate(proposal, worst_point, N=10, plot=True)

    proposal.forward_pass.assert_called_once_with(
        worst_point, rescale=True, compute_radius=True,
    )
    proposal.radius.assert_called_once_with(worst_z, worst_q)
    assert proposal.r == 1

    draw_calls = [
        call(2, r=1.0, N=5, fuzz=1.0, var=2.0),
        call(2, r=1.0, N=5, fuzz=1.0, var=2.0),
    ]
    proposal.draw_latent_prior.assert_has_calls(draw_calls)

    rejection_calls = [
        call(z[0], worst_q), call(z[1], worst_q), call(z[2], worst_q)
    ]
    proposal.rejection_sampling.assert_has_calls(rejection_calls)

    # TODO: call with
    proposal.plot_pool.assert_called_once()
    proposal.convert_to_samples.assert_called_once()

    assert proposal.population_acceptance == (10 / 15)
    assert proposal.populated_count == 2
    assert proposal.populated is True
