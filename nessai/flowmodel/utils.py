# -*- coding: utf-8 -*-
"""
Utilities for configuring FlowModel.
"""
import copy
from warnings import warn

from .config import DEFAULT_FLOW_CONFIG, DEFAULT_TRAINING_CONFIG
from ..flows.utils import get_n_neurons


def update_flow_config(cfg):
    """Update the model (flow) configuration dictionary based on the defaults.

    Parameters
    ----------
    d : Union[dict, None]
        Dictionary with the current configuration. If None, then the default is
        used.

    Returns
    -------
    dict
        Updated configuration dictionary.

    Raises
    ------
    TypeError
        Raised if the input is not a dictionary or None.
    """
    default = copy.deepcopy(DEFAULT_FLOW_CONFIG)
    if cfg is None:
        return default
    elif not isinstance(cfg, dict):
        raise TypeError(
            "Must pass a dictionary to update the default model config"
        )
    default.update(copy.deepcopy(cfg))
    default["n_neurons"] = get_n_neurons(
        n_neurons=default.get("n_neurons"),
        n_inputs=default.get("n_inputs"),
    )
    return default


def update_model_config(cfg):
    msg = """
    `update_model_config` is deprecated, use `update_flow_config` instead
    """
    warn(msg, FutureWarning)
    return update_flow_config(cfg)


def update_training_config(cfg):
    default = copy.deepcopy(DEFAULT_TRAINING_CONFIG)
    if cfg is None:
        return default
    elif not isinstance(cfg, dict):
        raise TypeError(
            "Must pass a dictionary to update the default model config"
        )
    default.update(copy.deepcopy(cfg))
    if default["noise_type"] is not None and default["noise_scale"] is None:
        raise RuntimeError(
            "`noise_scale` must be specified when `noise_type` is given."
        )
    if isinstance(default["noise_scale"], float):
        if default["noise_type"] is None:
            default["noise_type"] = "constant"
    elif default["noise_scale"] is not None:
        raise TypeError(
            "`noise_scale` must be a float. "
            f"'Got type: {type(default['noise_scale'])}"
        )
    return default


def update_config(flow_config, training_config=None):
    """
    Update the configuration dictionary to include the defaults.

    Notes
    -----
    The default configuration is specified in :py:mod:`nessai.flowmodel.config`


    The kwargs can contain any additional keyword arguments that are specific
    to the type of flow being used.

    Parameters
    ----------
    flow_config : dict
        Dictionary with flow configuration
    training_config : dict
        Dictionary with training config

    Returns
    -------
    dict
        Dictionary with updated flow configuration
    dict
        Dictionary with updated training configuration
    """
    if flow_config is not None and "model_config" in flow_config:
        msg = """
        Specifying `model_config` in `flow_config` is now deprecated.
        Please specify `flow_config` and `training_config` instead.
        """
        warn(msg, FutureWarning)
        training_config = copy.deepcopy(flow_config)
        flow_config = training_config.pop("model_config")

    if "device_tag" in flow_config:
        msg = """
        Specifying `device_tag` in `flow_config` is deprecated. It should now
        be specified in `training_config`.
        """
        warn(msg, FutureWarning)
        training_config = flow_config.pop("device_tag")

    if "inference_device_tag" in flow_config:
        msg = """
        Specifying `inference_device_tag` in `flow_config` is deprecated. It
        should now be specified in `training_config`.
        """
        warn(msg, FutureWarning)
        training_config = flow_config.pop("inference_device_tag")

    flow_config = update_flow_config(flow_config)
    training_config = update_training_config(training_config)
    return flow_config, training_config
