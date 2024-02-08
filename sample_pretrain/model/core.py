from abc import ABC

import torch
from torch import nn

from sample_pretrain.model.mamba import MixerModel
from sample_pretrain.model.model_utils import ModelModule
from sample_pretrain.utils.typing import Config

from mamba_ssm import Mamba as MambaLayer
from mamba_ssm.utils.generation import InferenceParams


class ModelCore(ModelModule, ABC):
    def __init__(self, cfg: Config):
        super().__init__(cfg)
        self.core_output_size = -1  # to be overridden in derived classes

    def get_out_size(self) -> int:
        return self.core_output_size

class CustomMamba(nn.Module):
    def __init__(self, input_size: int, output_size: int, d_model: int,
                 d_state: int, d_conv: int, expand: int, num_layers: int = 1):
        super().__init__()

        self.input_size = input_size
        self.output_size = output_size
        self.d_model = d_model
        self.d_state = d_state
        self.d_conv = d_conv
        self.expand = expand
        self.num_layers = num_layers

        ssm_cfg = {
           "d_state": d_state,
           "d_conv": d_conv,
           "expand": expand,
        }

        self.input_projection = nn.Linear(input_size, d_model)
        self.output_projection = nn.Linear(d_model, output_size)

        self.core = MixerModel(d_model, n_layer=num_layers, ssm_cfg=ssm_cfg)

    def forward(self, x, rnn_states):
        # states -> [num_layers, batch_size, d_state]

        # Handle rnn_states
        inference_params = InferenceParams(max_seqlen=3,
                                           max_batch_size=rnn_states.shape[1],
                                           seqlen_offset=2)
        rnn_states = rnn_states.reshape(self.num_layers, rnn_states.shape[1], -1, self.d_conv + self.d_state)
        rnn_states = rnn_states.contiguous().clone()
        conv_state = rnn_states[..., :self.d_conv]
        rnn_state = rnn_states[..., self.d_conv:]

        inference_params.key_value_memory_dict = {
            layer_idx: (conv_state[layer_idx], rnn_state[layer_idx])
            for layer_idx in range(self.num_layers)
        }

        # Process input
        x = self.input_projection(x)
        x = x.permute(1, 0, 2)
        x = self.core(x, inference_params=inference_params)
        x = x.permute(1, 0, 2)
        x = self.output_projection(x)

        conv_state = torch.stack(
            list(inference_params.key_value_memory_dict[layer_idx][0]
                 for layer_idx in range(self.num_layers)),
            dim=0
        )
        rnn_state = torch.stack(
            list(inference_params.key_value_memory_dict[layer_idx][1]
                 for layer_idx in range(self.num_layers)),
            dim=0
        )

        new_rnn_states = torch.cat((conv_state, rnn_state), dim=-1)
        new_rnn_states = new_rnn_states.reshape(self.num_layers, new_rnn_states.size(1), -1)

        return x, new_rnn_states


class ModelCoreRNN(ModelCore):
    def __init__(self, cfg, input_size):
        super().__init__(cfg)

        self.cfg = cfg
        self.is_gru = False
        self.is_mamba = False

        cfg.rnn_input_size = input_size

        if cfg.rnn_type == "gru":
            self.core = nn.GRU(input_size, cfg.rnn_size, cfg.rnn_num_layers)
            self.is_gru = True
        elif cfg.rnn_type == "lstm":
            self.core = nn.LSTM(input_size, cfg.rnn_size, cfg.rnn_num_layers)
        elif cfg.rnn_type == "mamba":
            self.is_mamba = True
            self.core = CustomMamba(input_size,
                                    output_size=cfg.rnn_size,
                                    d_model=cfg.mamba_model_size,
                                    d_state=cfg.mamba_state_size,
                                    d_conv=cfg.mamba_conv_size,
                                    expand=cfg.mamba_expand,
                                    num_layers=cfg.rnn_num_layers)
        else:
            raise RuntimeError(f"Unknown RNN type {cfg.rnn_type}")

        self.core_output_size = cfg.rnn_size
        self.rnn_num_layers = cfg.rnn_num_layers

    def forward(self, head_output, rnn_states):
        is_seq = not torch.is_tensor(head_output)
        
        if self.cfg.debug_zero_history:
            rnn_states = torch.zeros_like(rnn_states)

        if not is_seq:
            head_output = head_output.unsqueeze(0)

        if self.rnn_num_layers > 1:
            rnn_states = rnn_states.view(rnn_states.size(0), self.cfg.rnn_num_layers, -1)
            rnn_states = rnn_states.permute(1, 0, 2)
        else:
            rnn_states = rnn_states.unsqueeze(0)

        if self.is_mamba or self.is_gru:
            x, new_rnn_states = self.core(head_output, rnn_states.contiguous())
        else:
            # Just give zeros to LSTM
            h, c = torch.split(rnn_states, self.cfg.rnn_size, dim=2)
            x, (h, c) = self.core(head_output, (h.contiguous(), c.contiguous()))
            new_rnn_states = torch.cat((h, c), dim=2)

        if not is_seq:
            x = x.squeeze(0)

        if self.rnn_num_layers > 1:
            new_rnn_states = new_rnn_states.permute(1, 0, 2)
            new_rnn_states = new_rnn_states.reshape(new_rnn_states.size(0), -1)
        else:
            new_rnn_states = new_rnn_states.squeeze(0)

        return x, new_rnn_states


class ModelCoreIdentity(ModelCore):
    """A noop core (no recurrency)."""

    def __init__(self, cfg, input_size):
        super().__init__(cfg)
        self.cfg = cfg
        self.core_output_size = input_size

    # noinspection PyMethodMayBeStatic
    def forward(self, head_output, fake_rnn_states):
        return head_output, fake_rnn_states


def default_make_core_func(cfg: Config, core_input_size: int) -> ModelCore:
    if cfg.use_rnn:
        core = ModelCoreRNN(cfg, core_input_size)
    else:
        core = ModelCoreIdentity(cfg, core_input_size)

    return core
