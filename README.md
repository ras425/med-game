# Medical Diagnosis Game

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1ooqEnB_L95J1uk-ujM2bwyUA_AuVJfU_?usp=sharing)

- ask questions to guess the diagnosis
- game draws from 525 real clinical cases from USMLE medical exam database

**Dataset:** [MedQA on Hugging Face](https://huggingface.co/datasets/lavita/medical-qa-datasets)

## Play in Browser

Click the **Open in Colab** button above (no installation required). Just need a [Google AI API key](https://aistudio.google.com/apikey).

## Local Setup

```bash
pip install -r requirements.txt
```

Get a API key from [Google AI Studio](https://aistudio.google.com/apikey) (theres a free tier) and add to `config.yml` 

```yaml
api_key: "your-key-here"
```

Run:
```bash
python game.py
```

## How to play

1. read the patient's complaint and history
2. ask questions to get relevant test results, vitals, physical exam findings, etc
3. type `guess` when ready to submit your diagnosis
4. use `hint` to reveal additional findings
