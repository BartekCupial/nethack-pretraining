from mrunner.helpers.specification_helper import create_experiments_helper

name = globals()["script"][:-3]

# params for all exps
config = {
    "env": "nethack_challenge",
    "exp_tags": [name],
    "exp_point": "monk-AA-BC",
    "train_for_env_steps": 20_000_000_000,
    "group": "monk-AA-BC",
    "character": "mon-hum-neu",
    "num_workers": 16,
    "worker_num_splits": 2,
    "rollout": 32,
    "wandb_user": "rahid",
    "wandb_project": "sp_nethack",
    "wandb_group": "rahid",
    "with_wandb": True,
    "data_path": "/nle/nld-aa/nle_data",

    # Athena
    "db_path": "/ttyrecs/ttyrecs.db",
    "dataset_name": "autoascend",
    "batch_size": 512,

    # Local
    # "db_path": "/home/maciejwolczyk/Repos/ttyrecs.db",
    # "dataset_name": "nld-aa-taster-v1",
    # "batch_size": 16,

    "use_prev_action": True,
    "model": "ScaledNet",
    "use_resnet": True,
    "policy_initialization": "torch_default",
    "rnn_type": "mamba",
    "restart_behavior": "overwrite",
    "mamba_model_size": 256,
    "mamba_state_size": 8,
    "mamba_conv_size": 4,
    "mamba_expand": 2,
    "detach_hidden_state": False,
}

# params different between exps
params_grid = [
    {
        "seed": list(range(1)),
        "rnn_type": ["mamba"],
        "rnn_size": [512],
        "learning_rate": [1e-4, 5e-4, 1e-3],
        "max_grad_norm": [4.],
        "mamba_model_size": [256],
        "rnn_num_layers": [3],
        "rollout": [32],
        "mamba_use_complex": [False],
        "lr_schedule": ["interval_drop"],
        "lr_schedule_drop_step": [1_000_000_000, 2_000_000_000],
    },
]

experiments_list = create_experiments_helper(
    experiment_name=name,
    project_name="sp_nethack",
    with_neptune=False,
    script="./run.sh",
    python_path=".",
    tags=[name],
    base_config=config,
    params_grid=params_grid,
    mrunner_ignore=".mrunnerignore",
)
