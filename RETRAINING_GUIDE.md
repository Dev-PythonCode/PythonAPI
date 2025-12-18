# SpaCy NER Model Retraining Guide

## Current State (After Fixes)

**Issues Addressed:**
- ✅ Verb tokens like "guide", "find", "show" are now filtered out in the parser (not treated as skills)
- ✅ Python is correctly detected as TECHNOLOGY
- ✅ Experience extraction works for "with X years" patterns
- ✅ Role keyword fallback added for "developer", "engineer", etc.

**Parser Test Results:**
```
Query: "Guide me to become Python Developer"
  Skills: ['Python']  ← CORRECT (no "Guide")
  Applied filters: ['Skills: Python']

Query: "Find Python Developer with 5 years"
  Skills: ['Python']  ← CORRECT (no "Find")
  Applied filters: ['Skills: Python', 'Python: 5.0+ years']

Query: "Show me Python jobs"
  Skills: ['Python']  ← CORRECT (no "Show")
  Applied filters: ['Skills: Python']
```

## When to Retrain

Retrain the SpaCy model if you want to:
1. Improve entity recognition accuracy (F1 score)
2. Reduce false negatives (entities missed)
3. Add new entity types
4. Reduce false positives (misclassifications)

## Retraining Steps

### 1. Prepare Training Data

Update `data/complete_training_data.json` with annotated examples:

```json
[
  [
    "Guide me to become Python Developer",
    {"entities": [[13, 19, "TECHNOLOGY"], [23, 32, "ROLE"]]}
  ],
  [
    "Senior Python developer with 5+ years of Python experience",
    {"entities": [[0, 6, "SKILL_LEVEL"], [7, 13, "TECHNOLOGY"], [14, 23, "ROLE"], [29, 35, "TECH_EXPERIENCE"], [40, 46, "TECHNOLOGY"]]}
  ],
  ...
]
```

**Format:**
- Each entry: `[text, {"entities": [[start, end, label], ...]}]`
- Character offsets must be exact
- Labels: `TECHNOLOGY`, `TECH_CATEGORY`, `TECH_EXPERIENCE`, `OVERALL_EXPERIENCE`, `SKILL_LEVEL`, `ROLE`, `CERTIFICATION`

**Current dataset:** 62 examples in `data/complete_training_data.json`

### 2. Fix SpaCy Model Download (if needed)

The automatic model download may fail due to network issues. Download manually:

```bash
# Option A: Use pip with correct URL
.venv/bin/pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Option B: Use spacy CLI with fallback
.venv/bin/python -m spacy download en_core_web_sm-3.7.1
```

### 3. Run Training

```bash
cd /Users/dev/Projects/PythonAPI

# Train new model (takes 5-10 minutes)
.venv/bin/python train_spacy_model.py

# Test existing model without retraining
.venv/bin/python train_spacy_model.py --test-only

# Show training data statistics
.venv/bin/python train_spacy_model.py --stats
```

### 4. Verify Results

The script automatically tests trained model. Look for:
- Correct entity recognition on test queries
- No verb tokens extracted as skills
- Correct experience extraction (e.g., "5 years" → TECH_EXPERIENCE)

### 5. Deploy New Model

After training, the new model is saved to `./models/talent_ner_model/` and automatically loaded by `query_parser.py`.

Restart the Flask app to use the new model:
```bash
.venv/bin/python app.py
```

## Expanding Training Data

### Recommendations

1. **Add diverse negatives:** Examples with verbs that should NOT be extracted:
   ```json
   ["Help me find a Python developer", {"entities": [[13, 19, "TECHNOLOGY"], [20, 29, "ROLE"]]}]
   ```

2. **Add edge cases:**
   ```json
   ["Seeking AWS-certified architect in DevOps", {"entities": [[8, 11, "TECHNOLOGY"], [24, 33, "ROLE"], [37, 43, "TECH_CATEGORY"]]}]
   ```

3. **Add skill combinations:**
   ```json
   ["JavaScript and React developer", {"entities": [[0, 10, "TECHNOLOGY"], [15, 20, "TECHNOLOGY"], [21, 30, "ROLE"]]}]
   ```

4. **Add experience patterns:**
   ```json
   ["10-15 years in cloud infrastructure", {"entities": [[0, 7, "TECH_EXPERIENCE"], [11, 26, "TECH_CATEGORY"]]}]
   ```

### Tools for Faster Annotation

- **Label Studio**: Web-based labeling tool (recommended)
  ```bash
  docker run -p 8080:8080 heartexlabs/label-studio:latest
  ```

- **Prodigy**: Command-line annotation tool (commercial)
  ```bash
  prodigy ner.teach talent_ner_model ./data/raw_sentences.txt
  ```

### Target Dataset Size

- **Minimum:** 100 examples per entity type
- **Recommended:** 500+ diverse examples
- **High accuracy:** 1000+ examples with good coverage

## Model Configuration

Edit `train_spacy_model.py` to tune:

```python
# Training parameters
N_EPOCHS = 30          # Iterations over data (increase → longer training, possibly better)
BATCH_SIZE = 8         # Examples per update (decrease → slower but more precise)
DROPOUT = 0.3          # Regularization (increase → less overfitting)
```

## Performance Evaluation

After retraining, manually test:

```bash
.venv/bin/python - << 'EOF'
from services.query_parser import get_parser
p = get_parser()

tests = [
    "Guide me to become Python Developer",
    "Find Python Developer with 5 years",
    "Senior Java developer with 8 years total experience",
]

for q in tests:
    out = p.parse_query(q)
    print(f"Query: {q}")
    print(f"  Skills: {out['parsed']['skills']}")
    print(f"  Roles: {out['parsed']['roles']}")
    print(f"  Applied filters: {out['applied_filters']}\n")
EOF
```

## Troubleshooting

### "Can't find model en_core_web_sm"
→ Run: `.venv/bin/python -m spacy download en_core_web_sm`

### Training is slow
→ Reduce `N_EPOCHS` or `BATCH_SIZE` in train_spacy_model.py

### Model still misses entities
→ Add more training examples with those entity types

### Verb tokens still appearing as skills
→ Ensure verb is in `verb_tokens` set in `query_parser.py` line ~148 or line ~306

## Next Steps

1. **Immediate (no retraining needed):**
   - Parser now filters verbs → query quality improved
   - Test with end-users on real queries

2. **Short-term (1-2 weeks):**
   - Collect 50+ real user queries
   - Annotate them with correct labels
   - Retrain model

3. **Medium-term (1 month):**
   - Build annotation UI (Label Studio)
   - Set up continuous retraining pipeline
   - Monitor F1 score over time

## Related Files

- Training script: `train_spacy_model.py`
- Training data: `data/complete_training_data.json`
- Parser logic: `services/query_parser.py`
- Tech dictionary: `data/tech_dict_with_categories.json`
- Normalization map: `data/normalization_map.json`
