from typing import Tuple

from sample_pretrain.algo.runners.runner import Runner
from sample_pretrain.algo.utils.misc import ExperimentStatus
from sample_pretrain.cfg.arguments import maybe_load_from_checkpoint
from sample_pretrain.utils.typing import Config


def make_runner(cfg: Config) -> Tuple[Config, Runner]:
    if cfg.restart_behavior == "resume":
        # if we're resuming from checkpoint, we load all of the config parameters from the checkpoint
        # unless they're explicitly specified in the command line
        cfg = maybe_load_from_checkpoint(cfg)

    runner = Runner(cfg)

    return cfg, runner


def run_rl(cfg: Config):
    cfg, runner = make_runner(cfg)

    status = runner.init()
    if status == ExperimentStatus.SUCCESS:
        status = runner.run()

    return status


# load_nld_aa_large_dataset(
#                 role=role,
#                 race=race,
#                 align=align,
#                 **kwargs
#             )