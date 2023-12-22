#!/usr/bin/env bash

#SBATCH -o logger-%j.txt
#SBATCH --gres gpu:2 
#SBATCH --nodes 1
#SBATCH --mem=20G
#SBATCH -c 32
#SBATCH -t 2880
#SBATCH -A plgfoundationrl-gpu-a100
#SBATCH -p plgrid-gpu-a100
#SBATCH --nodelist=login01


singularity exec --nv \
    -H /net/people/plgrid/plgbartekcupial/sample-pretrain \
    --env WANDB_API_KEY=d2f9309c1cee36dc7ad726c57e4eba04974d9914 \
    --env WANDBPWD=$PWD \
    -B /net/pr2/projects/plgrid/plgggmum_crl/bcupial/nle:/nle \
    -B /net/pr2/projects/plgrid/plgggmum_crl/bcupial/ttyrecs:/ttyrecs \
    -B $TMPDIR:/tmp \
    /net/pr2/projects/plgrid/plgggmum_crl/bcupial/sp.sif \
    ./train.sh
