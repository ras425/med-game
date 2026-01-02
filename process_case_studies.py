"""
MedQA dataset: https://huggingface.co/datasets/lavita/medical-qa-datasets
Format: USMLE-style clinical vignettes with multiple choice answers
"""

import requests
import io
import re
import random
import pyarrow.parquet as pq

DATASET_URL = "https://huggingface.co/datasets/lavita/medical-qa-datasets/resolve/main/medical_meadow_medqa/train-00000-of-00001-1f3ce4c784562e9c.parquet"

# Keywords indicating test results (want to hide these from initial presentation)
TEST_KEYWORDS = [
    r'\bECG\b', r'\bEKG\b', r'\bCT\b', r'\bMRI\b', r'\bX-ray\b', r'\bultrasound\b',
    r'\bbiopsy\b', r'\bhistology\b', r'\blaboratory\b', r'\blab\s', r'\blabs\b',
    r'\bWBC\b', r'\bRBC\b', r'\bhemoglobin\b', r'\bplatelet', r'\bcreatinine\b',
    r'\bALT\b', r'\bAST\b', r'\btroponin\b', r'\bD-dimer\b', r'\bTSH\b',
    r'\burinalysis\b', r'\bculture\b', r'\bPCR\b', r'\becho\b', r'\bangiograph',
    r'\bmg/dL\b', r'\bmmol\b', r'\bU/L\b', r'\bng/mL\b', r'\bSpO2\b',
    r'\bvital\s+signs?\b', r'\bBP\b', r'\bblood pressure\b', r'\bpulse\b',
    r'\bHR\b', r'\bRR\b', r'\btemperature\b', r'\bphysical exam',
    r'\bmurmur\b', r'\bcrackles\b', r'\brales\b', r'\bwheezing\b',
    r'reveal(s|ed)?', r'show(s|ed)?', r'demonstrat(e|es|ed)', r'confirm(s|ed)?',
]

# Disease name patterns (answers must contain these)
DISEASE_PATTERNS = [
    "disease", "syndrome", "disorder", "itis", "osis", "emia", "pathy",
    "oma", "carcinoma", "lymphoma", "leukemia", "anemia", "failure",
    "infection", "infarction", "embolism", "thrombosis", "bursitis",
    "stenosis", "insufficiency", "hypertension", "hypotension",
    "cancer", "tumor", "abscess", "fracture", "rupture", "palsy",
    "sclerosis", "fibrosis", "necrosis", "cirrhosis", "psychosis",
    "asthma", "epilepsy", "migraine", "stroke", "attack", "arrest",
    "hernia", "ulcer", "pneumonia", "sepsis", "shock", "coma"
]

# Words that indicate non-diagnosis answers
BAD_ANSWER_WORDS = [
    "accumulation", "blockade", "release", "migration", "mutation",
    "increase", "decrease", "sensitivity", "specificity", "%", "=",
    "positive", "negative", "high", "low", "type a", "type b",
    "should", "could", "would", "history of", "compression of",
    "the patient", "vaccination", "microcytosis", "macrocytosis", "level"
]

_cached_cases = None
_parquet_data = None


def parse_case(row) -> dict | None:
    """Parse a dataset row into a case dictionary."""
    input_text = row['input']
    output_text = row['output']
    
    if not input_text or not output_text:
        return None
    
    # extract question and options
    match = re.match(r"Q:(.*?\?)\s*(\{.*\})", input_text, re.DOTALL)
    if not match:
        return None
    
    question_text = match.group(1).strip()
    options_str = match.group(2).rstrip(',')
    
    try:
        options = eval(options_str)
    except:
        return None
    
    # Parse answer: "E: Hirschsprung disease"
    answer_match = re.match(r"([A-E]):\s*(.+)", output_text.strip())
    if not answer_match:
        return None
    
    answer_letter = answer_match.group(1)
    diagnosis = answer_match.group(2).strip()
    
    # Filter: must be a diagnosis question
    question_lower = question_text.lower()
    diagnosis_keywords = ["diagnosis", "most likely", "condition", "disease", "disorder", "syndrome"]
    if not any(kw in question_lower for kw in diagnosis_keywords):
        return None
    
    # Filter: exclude mechanism/treatment questions
    exclude_keywords = ["mechanism", "pathophysiology", "treatment", "drug", "medication",
                       "prevent", "manage", "therapy", "next step", "best initial"]
    if any(kw in question_lower for kw in exclude_keywords):
        return None
    
    # Filter: answer must look like a disease name
    answer_lower = diagnosis.lower()
    if any(bw in answer_lower for bw in BAD_ANSWER_WORDS):
        return None
    if len(diagnosis) > 50:
        return None
    
    has_disease_pattern = any(dp in answer_lower for dp in DISEASE_PATTERNS)
    has_eponym = bool(re.search(r"[A-Z][a-z]+['\s]s?\s", diagnosis))
    if not has_disease_pattern and not has_eponym:
        return None
    
    # split into sentences
    sentences = question_text.split('. ')
    if len(sentences) < 2:
        return None
    
    case_text = '. '.join(sentences[:-1]) + '.'
    if len(case_text) < 100:
        return None
    
    # Separate presentation from test results
    presentation = []
    findings = []
    
    for sent in case_text.split('. '):
        sent = sent.strip()
        if not sent:
            continue
        is_finding = any(re.search(kw, sent, re.IGNORECASE) for kw in TEST_KEYWORDS)
        (findings if is_finding else presentation).append(sent)
    
    if len(presentation) < 1:
        return None
    
    description = '. '.join(presentation)
    if not description.endswith('.'):
        description += '.'
    
    details = '. '.join(findings)
    if details and not details.endswith('.'):
        details += '.'
    
    if len(description) < 50:
        return None
    
    return {
        "description": description,
        "details": details,
        "diagnosis": diagnosis,
        "options": options,
        "correct_letter": answer_letter,
    }


def load_cases(num_cases: int = 100) -> list:
    """Load medical cases from MedQA dataset."""
    global _cached_cases, _parquet_data
    
    if _cached_cases and len(_cached_cases) >= num_cases:
        return random.sample(_cached_cases, min(num_cases, len(_cached_cases)))
    
    print("Loading real medical cases from MedQA dataset...")
    
    if _parquet_data is None:
        resp = requests.get(DATASET_URL, timeout=60)
        resp.raise_for_status()
        _parquet_data = resp.content
    
    table = pq.read_table(io.BytesIO(_parquet_data))
    df = table.to_pandas()
    
    cases = []
    seen = set()
    
    for _, row in df.iterrows():
        if len(cases) >= num_cases * 2:
            break
        
        case = parse_case(row)
        if not case:
            continue
        
        diag = case['diagnosis'].lower()
        if diag in seen:
            continue
        seen.add(diag)
        cases.append(case)
    
    _cached_cases = cases
    print(f"Loaded {len(cases)} cases.")
    
    return random.sample(cases, min(num_cases, len(cases)))
