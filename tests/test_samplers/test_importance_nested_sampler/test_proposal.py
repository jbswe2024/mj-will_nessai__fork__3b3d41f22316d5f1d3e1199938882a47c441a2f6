"""Tests for the proposals and meta-proposal"""
from unittest.mock import MagicMock

from nessai.samplers.importancesampler import ImportanceNestedSampler as INS
from nessai.utils.testing import assert_structured_arrays_equal
import numpy as np
import pytest


@pytest.fixture()
def ins(ins, proposal):
    ins.proposal = proposal
    return ins


@pytest.mark.parametrize("weighted_kl", [False, True])
def test_add_new_proposal(ins, samples, log_q, weighted_kl):

    n = int(0.8 * len(samples))

    ins.samples = np.sort(samples, order="logL")
    ins.log_q = log_q
    ins.logL_threshold = ins.samples[n]["logL"]

    ins.replace_all = False
    ins.weighted_kl = weighted_kl
    ins.plot_training_data = True
    ins.training_time = 0.0

    INS.add_new_proposal(ins)

    ins.proposal.train.assert_called_once()
    assert_structured_arrays_equal(
        ins.proposal.train.call_args_list[0][0][0], ins.samples[n:]
    )


def test_draw_n_samples(ins, samples, log_q, history):
    expected = samples.copy()
    n = len(expected)
    ins.draw_samples_time = 0.0
    ins.model.batch_evaluate_log_likelihood = MagicMock(
        return_value=samples["logL"].copy()
    )
    samples["logL"] = np.nan
    ins.proposal.draw = MagicMock(return_value=(samples, log_q))
    ins.history = history
    ins.compute_leakage = MagicMock(return_value=0.1)

    out = INS.draw_n_samples(ins, n)

    ins.proposal.draw.assert_called_once_with(n)

    assert ins.history["leakage_new_points"][-1] == 0.1

    np.testing.assert_array_equal(out[1], log_q)
    assert_structured_arrays_equal(out[0], expected)
