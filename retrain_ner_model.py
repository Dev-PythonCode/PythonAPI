#!/usr/bin/env python3
"""
Retrain SpaCy NER model with expanded training data including CAREER_SKILLS entity
This includes 14,167 training examples with better coverage of career variations
"""

import spacy
from spacy.training import Example
import random
import json
from pathlib import Path

def train_spacy_model(
    output_dir='./models/talent_ner_model',
    training_data_path='./data/complete_training_data.json',
    n_epochs=30,
    batch_size=8,
    dropout=0.3
):
    """Train SpaCy NER model with career roadmap training data"""
    
    print("="*60)
    print("🚀 SPACY NER MODEL RETRAINING")
    print("="*60)
    
    # Load training data
    print(f"\n📂 Loading training data from {training_data_path}...")
    with open(training_data_path, 'r') as f:
        training_data = json.load(f)
    
    print(f"✅ Loaded {len(training_data)} training examples")
    
    # Create blank model or load existing
    print("\n🔧 Creating blank spaCy model with 'en' language...")
    nlp = spacy.blank('en')
    
    # Add entity recognizer
    if 'ner' not in nlp.pipe_names:
        ner = nlp.add_pipe('ner', last=True)
    else:
        ner = nlp.get_pipe('ner')
    
    # Get all unique entity labels from training data
    entity_labels = set()
    for text, annotations in training_data:
        if 'entities' in annotations:
            for start, end, label in annotations['entities']:
                entity_labels.add(label)
    
    print(f"✅ Found {len(entity_labels)} unique entity labels:")
    for label in sorted(entity_labels):
        print(f"   - {label}")
        ner.add_label(label)
    
    # Disable other pipes
    print("\n⚙️  Configuring model pipes...")
    pipe_exceptions = ['ner', 'tagger', 'parser']
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe not in pipe_exceptions]
    
    # Prepare training examples
    print(f"\n📊 Preparing {len(training_data)} training examples...")
    examples = []
    for text, annotations in training_data:
        try:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            examples.append(example)
        except Exception as e:
            print(f"   ⚠️  Skipped malformed example: {text[:50]}...")
    
    print(f"✅ Prepared {len(examples)} valid training examples")
    
    # Training loop
    print(f"\n🎯 Starting training ({n_epochs} epochs, batch_size={batch_size}, dropout={dropout})...")
    print("-" * 60)
    
    for epoch in range(n_epochs):
        random.shuffle(examples)
        losses = {}
        
        # Create mini-batches
        for i in range(0, len(examples), batch_size):
            batch = examples[i:i+batch_size]
            
            with nlp.select_pipes(disable=other_pipes):
                nlp.update(
                    batch,
                    sgd=nlp.create_optimizer(),
                    drop=dropout,
                    losses=losses
                )
        
        # Print progress every 5 epochs
        if (epoch + 1) % 5 == 0:
            loss_value = losses.get('ner', 0)
            print(f"Epoch {epoch+1:3d}/{n_epochs} | Loss: {loss_value:.4f}")
    
    print("-" * 60)
    
    # Save model
    print(f"\n💾 Saving model to {output_dir}...")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(output_path)
    print(f"✅ Model saved successfully!")
    
    # Test on sample data
    print(f"\n🧪 Testing trained model on sample prompts:")
    print("-" * 60)
    
    test_prompts = [
        "python coder",
        "python programmer",
        "angular based UI developer",
        "sql database engineer",
        "machine learning specialist"
    ]
    
    for prompt in test_prompts:
        doc = nlp(prompt)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        print(f"'{prompt}':")
        if entities:
            for text, label in entities:
                print(f"   ✓ '{text}' → {label}")
        else:
            print(f"   ✗ No entities detected")
    
    print("\n" + "="*60)
    print("✅ RETRAINING COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Test with new model: python3 -c \"from services.career_roadmap import get_roadmap_service\"")
    print("2. Verify career path matching with various prompts")
    print("3. Deploy model to production")

if __name__ == '__main__':
    train_spacy_model()
