---
name: slurm-job
description: Generate SLURM/cluster job submission scripts
---

# SLURM Job Script Generator

Generate job submission scripts for compute clusters (SLURM, PBS, LSF).

## Instructions

1. Ask for: number of GPUs, training script, estimated time, memory needs
2. Generate appropriate submission script
3. Include common patterns: multi-node, array jobs, dependency chains

## SLURM Templates

### Single GPU Training
```bash
#!/bin/bash
#SBATCH --job-name=train_model
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%j_%x.out
#SBATCH --error=logs/%j_%x.err

module load cuda/12.1
source activate myenv

python train.py \
    --config configs/default.yaml \
    --output_dir outputs/$SLURM_JOB_ID
```

### Multi-GPU (Single Node)
```bash
#!/bin/bash
#SBATCH --job-name=train_multigpu
#SBATCH --partition=gpu
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --time=48:00:00
#SBATCH --output=logs/%j_%x.out

module load cuda/12.1
source activate myenv

torchrun --nproc_per_node=4 \
    train.py \
    --config configs/default.yaml \
    --dist_backend nccl
```

### Multi-Node Distributed
```bash
#!/bin/bash
#SBATCH --job-name=train_distributed
#SBATCH --partition=gpu
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=4
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=8
#SBATCH --mem=256G
#SBATCH --time=72:00:00
#SBATCH --output=logs/%j_%x.out

module load cuda/12.1
source activate myenv

export MASTER_ADDR=$(scontrol show hostnames $SLURM_JOB_NODELIST | head -n 1)
export MASTER_PORT=29500

srun torchrun \
    --nnodes=$SLURM_NNODES \
    --nproc_per_node=4 \
    --rdzv_id=$SLURM_JOB_ID \
    --rdzv_backend=c10d \
    --rdzv_endpoint=$MASTER_ADDR:$MASTER_PORT \
    train.py --config configs/default.yaml
```

### Hyperparameter Sweep (Array Job)
```bash
#!/bin/bash
#SBATCH --job-name=sweep
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --array=0-9
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%A_%a.out

LR_VALUES=(1e-3 5e-4 1e-4 5e-5 1e-5 3e-4 7e-4 2e-4 8e-5 3e-5)
LR=${LR_VALUES[$SLURM_ARRAY_TASK_ID]}

python train.py \
    --config configs/default.yaml \
    --lr $LR \
    --output_dir outputs/sweep_lr_${LR}
```

### Job Dependency Chain
```bash
# Train → Evaluate → Generate figures
JOB1=$(sbatch --parsable train.sh)
JOB2=$(sbatch --parsable --dependency=afterok:$JOB1 evaluate.sh)
sbatch --dependency=afterok:$JOB2 plot_results.sh
```

### With Accelerate/DeepSpeed
```bash
#!/bin/bash
#SBATCH --job-name=train_ds
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --time=48:00:00

accelerate launch \
    --config_file configs/accelerate_config.yaml \
    --num_processes 4 \
    train.py --config configs/default.yaml

# Or with DeepSpeed:
# deepspeed --num_gpus=4 train.py \
#     --deepspeed configs/ds_config.json
```

## Useful Patterns

### Auto-resume from checkpoint
```bash
CKPT_DIR=outputs/$SLURM_JOB_ID
if [ -f "$CKPT_DIR/latest_checkpoint.pt" ]; then
    RESUME_FLAG="--resume $CKPT_DIR/latest_checkpoint.pt"
else
    RESUME_FLAG=""
fi
python train.py $RESUME_FLAG --output_dir $CKPT_DIR
```

### Email notification
```bash
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=your@email.com
```

### Resource monitoring
```bash
# Add to script for GPU monitoring
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used --format=csv -l 60 > logs/gpu_${SLURM_JOB_ID}.csv &
```

## Tips
- Always create `logs/` directory before submitting
- Use `%j` (job ID) in output filenames to avoid overwrites
- Set `--time` generously but not excessively (affects scheduling priority)
- Use `--constraint` for specific GPU types (e.g., `--constraint=a100`)
- Add `--requeue` for fault tolerance on preemptible partitions
