---
name: experiment
description: 管理实验日志——创建实验、关联 wandb、记录结论、追踪假设验证
---

# Experiment Journal — 实验日志

结构化记录实验，与 wandb 打通，绑定到具体假设。

## 使用场景

### 开始新实验
```
/experiment
> 新实验：测试 X 方法在 Y 数据集上的效果
```

Claude 会引导你填写：
1. 假设（要验证什么）
2. 实验设计（模型、数据、关键超参）
3. wandb 项目和 run ID（可选）

### 实验完成后
```
/experiment
> 更新 EXP-001 结果
```

Claude 会：
1. 从 wandb 拉取 metrics
2. 帮你写结论
3. 决定下一步

## Instructions

1. **新实验**: 调用 `create_experiment(title, hypothesis, design, wandb_project, wandb_run_id)`
2. **查看实验**: 调用 `list_experiments()` 或 `experiment_summary()`
3. **拉取 wandb 数据**: 调用 `get_wandb_run(project, run_id)` 获取 config 和 metrics
4. **更新实验**: 调用 `update_experiment(exp_id, status, conclusion, results)`
5. **实验失败时**: 
   - 将 status 设为 "failed"
   - 将失败原因记录到 conclusion
   - 建议用户更新 Working/idea-pool.md 的 Killed Ideas

## 与 idea-pool 的联动

- 每个实验应关联到 idea-pool 中的一个想法
- 成功的实验验证假设 → 想法晋升到 Evolving 层
- 失败的实验 → 记录原因到 Killed Ideas，避免重复尝试

## 实验状态流转

```
🏃 Running → ✅ Completed (假设验证成功)
🏃 Running → ❌ Failed (假设被推翻)
🏃 Running → ⏸️ Paused (需要更多资源/时间)
⏸️ Paused → 🏃 Running (恢复)
```
