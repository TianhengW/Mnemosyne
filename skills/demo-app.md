---
name: demo-app
description: Quickly build Gradio/Streamlit demos for research
---

# Demo App Builder

Quickly scaffold interactive demos for research projects using Gradio or Streamlit.

## Instructions

1. Understand what the model does (input/output format)
2. Choose the right framework:
   - **Gradio**: Best for ML demos, HuggingFace Spaces integration, quick API
   - **Streamlit**: Best for dashboards, multi-page apps, data exploration
3. Generate the demo code
4. Provide deployment instructions

## Gradio Templates

### Text-to-Text (LLM/NLP)
```python
import gradio as gr
from model import load_model, generate

model = load_model("path/to/checkpoint")

def predict(input_text, temperature=0.7, max_tokens=256):
    output = generate(model, input_text, temperature=temperature, max_tokens=max_tokens)
    return output

demo = gr.Interface(
    fn=predict,
    inputs=[
        gr.Textbox(label="Input", lines=5, placeholder="Enter your prompt..."),
        gr.Slider(0.1, 2.0, value=0.7, label="Temperature"),
        gr.Slider(64, 1024, value=256, step=64, label="Max Tokens"),
    ],
    outputs=gr.Textbox(label="Output", lines=10),
    title="My Research Model Demo",
    description="[Paper Title] - interactive demo",
    examples=[
        ["Example input 1", 0.7, 256],
        ["Example input 2", 0.5, 512],
    ],
)

demo.launch(share=True)
```

### Image + Text (VLM)
```python
import gradio as gr

def predict(image, question):
    # Process with VLM
    answer = model.generate(image, question)
    return answer

demo = gr.Interface(
    fn=predict,
    inputs=[
        gr.Image(type="pil", label="Upload Image"),
        gr.Textbox(label="Question"),
    ],
    outputs=gr.Textbox(label="Answer"),
    title="VLM Reasoning Demo",
)
```

### Comparison / A-B Testing
```python
import gradio as gr

def compare(input_text):
    result_a = model_a.generate(input_text)
    result_b = model_b.generate(input_text)
    return result_a, result_b

demo = gr.Interface(
    fn=compare,
    inputs=gr.Textbox(label="Input"),
    outputs=[
        gr.Textbox(label="Baseline"),
        gr.Textbox(label="Ours"),
    ],
)
```

### Chat Interface
```python
import gradio as gr

def respond(message, history):
    # history is list of [user_msg, bot_msg] pairs
    context = "\n".join([f"User: {h[0]}\nAssistant: {h[1]}" for h in history])
    response = model.generate(context + f"\nUser: {message}\nAssistant:")
    return response

demo = gr.ChatInterface(
    fn=respond,
    title="Research Agent Chat",
    examples=["Explain your reasoning", "What would happen if..."],
)
```

## Streamlit Template

### Results Dashboard
```python
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Experiment Results", layout="wide")
st.title("📊 Experiment Dashboard")

# Sidebar controls
experiment = st.sidebar.selectbox("Experiment", ["ablation", "main", "scaling"])
metric = st.sidebar.selectbox("Metric", ["accuracy", "loss", "f1"])

# Load results
df = pd.read_csv(f"results/{experiment}.csv")

# Plot
col1, col2 = st.columns(2)
with col1:
    fig = px.line(df, x="step", y=metric, color="method", title=f"{metric} over training")
    st.plotly_chart(fig)

with col2:
    fig = px.bar(df.groupby("method")[metric].max().reset_index(), 
                 x="method", y=metric, title=f"Best {metric}")
    st.plotly_chart(fig)

# Raw data
st.dataframe(df)
```

## Deployment

### HuggingFace Spaces (Free GPU)
```bash
# Create Space
huggingface-cli repo create my-demo --type space --space-sdk gradio

# Push code
cd my-demo
git add app.py requirements.txt
git commit -m "Initial demo"
git push
```

### Requirements for demo
```txt
gradio>=4.0.0
torch>=2.0.0
transformers>=4.35.0
# your model dependencies
```

## Tips
- Keep the demo focused on ONE thing the model does well
- Include 3-5 pre-loaded examples that showcase strengths
- Add a "paper" link and citation in the description
- For expensive models, add a queue: `demo.queue().launch()`
- Cache predictions: `@gr.cache` or `@st.cache_data`
- For CVPR/NeurIPS supplementary: record a video of the demo
