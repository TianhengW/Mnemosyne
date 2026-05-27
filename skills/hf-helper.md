---
name: hf-helper
description: HuggingFace Transformers/PEFT/Datasets usage guide and code generation
---

# HuggingFace Helper

Expert guidance on using the HuggingFace ecosystem for research: Transformers, PEFT, Datasets, Trainer, Accelerate.

## Quick References

### Loading Models

```python
# Standard model loading
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    torch_dtype=torch.bfloat16,
    device_map="auto",
    attn_implementation="flash_attention_2",
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

# Vision-Language Model
from transformers import AutoProcessor, AutoModelForVision2Seq
model = AutoModelForVision2Seq.from_pretrained("llava-hf/llava-v1.6-mistral-7b-hf")
processor = AutoProcessor.from_pretrained("llava-hf/llava-v1.6-mistral-7b-hf")
```

### PEFT / LoRA Fine-tuning

```python
from peft import LoraConfig, get_peft_model, TaskType

lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    bias="none",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# trainable params: 0.5% of total
```

### QLoRA (4-bit quantized)

```python
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
)
# Then apply LoRA on top
```

### Training with Trainer

```python
from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    output_dir="./outputs",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,
    learning_rate=2e-5,
    weight_decay=0.01,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    bf16=True,
    logging_steps=10,
    save_strategy="epoch",
    evaluation_strategy="epoch",
    report_to="wandb",
    gradient_checkpointing=True,
    dataloader_num_workers=4,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=data_collator,
)
trainer.train()
```

### Custom Dataset

```python
from datasets import Dataset, load_dataset

# From HuggingFace Hub
dataset = load_dataset("tatsu-lab/alpaca")

# From local files
dataset = load_dataset("json", data_files="data/train.jsonl")

# Custom processing
def preprocess(examples):
    texts = [f"Question: {q}\nAnswer: {a}" 
             for q, a in zip(examples["question"], examples["answer"])]
    tokenized = tokenizer(texts, truncation=True, max_length=512, padding="max_length")
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

dataset = dataset.map(preprocess, batched=True, remove_columns=dataset.column_names)
```

### Generation / Inference

```python
# Standard generation
inputs = tokenizer("Once upon a time", return_tensors="pt").to(model.device)
outputs = model.generate(
    **inputs,
    max_new_tokens=256,
    temperature=0.7,
    top_p=0.9,
    do_sample=True,
    repetition_penalty=1.1,
)
text = tokenizer.decode(outputs[0], skip_special_tokens=True)

# Batch generation with vLLM (faster)
from vllm import LLM, SamplingParams
llm = LLM(model="meta-llama/Llama-3.1-8B")
outputs = llm.generate(prompts, SamplingParams(temperature=0.7, max_tokens=256))
```

### With Accelerate (Multi-GPU)

```python
from accelerate import Accelerator

accelerator = Accelerator(mixed_precision="bf16")
model, optimizer, dataloader = accelerator.prepare(model, optimizer, dataloader)

for batch in dataloader:
    outputs = model(**batch)
    loss = outputs.loss
    accelerator.backward(loss)
    optimizer.step()
    optimizer.zero_grad()
```

## Common Patterns for Research

### Custom Loss with Trainer
```python
class CustomTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        outputs = model(**inputs)
        # Custom loss computation
        loss = my_custom_loss(outputs.logits, inputs["labels"])
        return (loss, outputs) if return_outputs else loss
```

### Reward Model Training (RLHF)
```python
from trl import RewardTrainer, RewardConfig

training_args = RewardConfig(
    output_dir="./reward_model",
    per_device_train_batch_size=4,
    num_train_epochs=1,
    gradient_checkpointing=True,
)
trainer = RewardTrainer(
    model=model,
    args=training_args,
    train_dataset=preference_dataset,
    tokenizer=tokenizer,
)
```

### DPO / GRPO Training
```python
from trl import DPOTrainer, DPOConfig

dpo_config = DPOConfig(
    beta=0.1,
    output_dir="./dpo_output",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
)
trainer = DPOTrainer(
    model=model,
    ref_model=ref_model,
    args=dpo_config,
    train_dataset=preference_data,
    tokenizer=tokenizer,
)
```

## Debugging Tips
- `model.config` to inspect architecture
- `tokenizer.decode(input_ids[0])` to verify tokenization
- `model.print_trainable_parameters()` with PEFT
- `accelerate config` to set up multi-GPU
- `TRANSFORMERS_CACHE` env var to control cache location
