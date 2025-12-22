#!/usr/bin/env python3
"""
Incrementally retrain existing SpaCy NER model with new CAREER_SKILLS entity variations
This preserves the existing model's knowledge while adding new training data
"""

import spacy
from spacy.training import Example
import random
import json
from pathlib import Path
import sys

def retrain_existing_model(
    model_dir='./models/talent_ner_model',
    training_data_path='./data/complete_training_data.json',
    n_epochs=15,
    batch_size=16,
    dropout=0.2
):
    """Incrementally retrain existing SpaCy NER model"""
    
    print("="*70)
    print("🔄 INCREMENTAL SPACY NER MODEL RETRAINING")
    print("="*70)
    
    # Load existing model
    print(f"\n📦 Loading existing model from {model_dir}...")
    try:
        nlp = spacy.load(model_dir)
        print("✅ Successfully loaded existing model")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("   Creating new blank model instead...")
        nlp = spacy.blank('en')
        if 'ner' not in nlp.pipe_names:
            nlp.add_pipe('ner', last=True)
    
    # Load training data (main + optional additional file)
    print(f"\n📂 Loading training data from {training_data_path} and optional additional file...")
    training_data = []
    main_path = Path(training_data_path)
    if main_path.exists():
        with main_path.open('r') as f:
            try:
                main_data = json.load(f)
                if isinstance(main_data, list):
                    training_data.extend(main_data)
            except Exception as e:
                print(f"⚠️  Could not load main training data: {e}")
    else:
        print(f"⚠️  Main training file not found: {training_data_path}")

    # Optional additional examples file
    additional_path = Path('data/additional_career_skills.json')
    if additional_path.exists():
        with additional_path.open('r') as f:
            try:
                add_data = json.load(f)
                if isinstance(add_data, list):
                    training_data.extend(add_data)
                    print(f"✅ Merged {len(add_data)} additional examples from {additional_path}")
            except Exception as e:
                print(f"⚠️  Could not load additional training data: {e}")

    print(f"✅ Total loaded training examples: {len(training_data)}")
    
    # Get NER component
    ner = nlp.get_pipe('ner')
    
    # Get all unique entity labels from training data
    print("\n🏷️  Identifying entity labels...")
    entity_labels = set()
    skipped_malformed = 0
    
    for idx, item in enumerate(training_data):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            skipped_malformed += 1
            continue
        
        text, annotations = item
        if not isinstance(annotations, dict) or 'entities' not in annotations:
            skipped_malformed += 1
            continue
        
        for entity in annotations['entities']:
            if isinstance(entity, (list, tuple)) and len(entity) >= 3:
                label = entity[2]
                entity_labels.add(label)
    
    print(f"✅ Found {len(entity_labels)} unique entity labels:")
    for label in sorted(entity_labels):
        if label not in ner.labels:
            try:
                ner.add_label(label)
                print(f"   ✓ Added label: {label}")
            except Exception as e:
                print(f"   ⚠️  Could not add label {label}: {e}")
        else:
            print(f"   ✓ Label already exists: {label}")
    
    print(f"⚠️  Skipped {skipped_malformed} malformed examples")
    
    # Prepare training examples
    print(f"\n📊 Preparing training examples...")
    examples = []
    failed_examples = 0
    
    for idx, item in enumerate(training_data):
        try:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            
            text, annotations = item
            if not isinstance(text, str) or not isinstance(annotations, dict):
                continue
            
            if 'entities' not in annotations:
                continue
            
            # Validate entities
            valid_entities = []
            for entity in annotations['entities']:
                if not isinstance(entity, (list, tuple)) or len(entity) < 3:
                    continue
                start, end, label = entity[0], entity[1], entity[2]
                
                # Check bounds
                if not isinstance(start, int) or not isinstance(end, int):
                    continue
                if start < 0 or end > len(text) or start >= end:
                    continue
                
                try:
                    # Verify we can extract the text
                    extracted = text[start:end]
                    if len(extracted) > 0:
                        valid_entities.append((start, end, label))
                except:
                    continue
            
            if not valid_entities:
                continue
            
            # Create example
            doc = nlp.make_doc(text)
            example = Example.from_dict(
                doc,
                {"entities": valid_entities}
            )
            examples.append(example)
            
        except Exception as e:
            failed_examples += 1
            if failed_examples <= 3:  # Log first 3 failures
                print(f"   ⚠️  Failed to process example {idx}: {str(e)[:50]}")
    
    print(f"✅ Prepared {len(examples)} valid training examples")
    if failed_examples > 0:
        print(f"⚠️  {failed_examples} examples could not be processed")
    
    # Training configuration
    print(f"\n🎯 Training configuration:")
    print(f"   - Epochs: {n_epochs}")
    print(f"   - Batch size: {batch_size}")
    print(f"   - Dropout: {dropout}")
    print(f"   - Training examples: {len(examples)}")
    print("-" * 70)
    
    # Training loop
    best_loss = float('inf')
    patience = 3
    no_improve_count = 0
    
    for epoch in range(n_epochs):
        try:
            random.shuffle(examples)
            losses = {}
            
            # Create mini-batches and train
            for batch_idx in range(0, len(examples), batch_size):
                batch = examples[batch_idx:batch_idx+batch_size]
                
                try:
                    nlp.update(
                        batch,
                        drop=dropout,
                        sgd=nlp.create_optimizer(),
                        losses=losses
                    )
                except Exception as e:
                    # Log but continue with next batch
                    if epoch == 0 and batch_idx < 100:
                        print(f"   ⚠️  Batch {batch_idx}: {str(e)[:60]}")
                    continue
            
            # Monitor loss
            loss_value = losses.get('ner', 0.0)
            
            # Print progress
            if (epoch + 1) % 3 == 0 or epoch == 0:
                print(f"Epoch {epoch+1:2d}/{n_epochs} | Loss: {loss_value:.4f}")
            
            # Early stopping
            if loss_value < best_loss:
                best_loss = loss_value
                no_improve_count = 0
            else:
                no_improve_count += 1
                if no_improve_count >= patience:
                    print(f"⏹️  Early stopping at epoch {epoch + 1} (loss not improving)")
                    break
        
        except KeyboardInterrupt:
            print("\n⏹️  Training interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error at epoch {epoch + 1}: {e}")
            continue
    
    print("-" * 70)
    
    # Save model
    print(f"\n💾 Saving retrained model to {model_dir}...")
    try:
        nlp.to_disk(model_dir)
        print(f"✅ Model saved successfully!")
    except Exception as e:
        print(f"❌ Error saving model: {e}")
        sys.exit(1)
    
    # Test on sample data
    print(f"\n🧪 Testing retrained model on sample prompts:")
    print("-" * 70)
    
    test_prompts = [
        "python coder",
        "python programmer",
        "angular based UI developer",
        "angular frontend engineer",
        "sql database specialist",
        "machine learning engineer",
        "backend python developer"
    ]
    
    for prompt in test_prompts:
        doc = nlp(prompt)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        print(f"  '{prompt}'")
        if entities:
            for text, label in entities:
                print(f"      ✓ '{text}' → {label}")
        else:
            print(f"      ✗ No entities detected")
    
    print("\n" + "="*70)
    print("✅ RETRAINING COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Test career path matching: python3 app.py")
    print("2. Try prompts like 'python coder', 'angular programmer', etc.")
    print("3. Verify model matches to correct career paths")

if __name__ == '__main__':
    retrain_existing_model()
