import json
import os
from typing import Dict, Any, List
import logging

from services.query_parser import get_parser
import re

logger = logging.getLogger(__name__)


class CareerRoadmapService:
    def __init__(self, training_path: str = './data/career_roadmap_training.json'):
        self.parser = get_parser()
        self.training = {}
        self.training_path = training_path
        self.load_training()

    def load_training(self):
        if os.path.exists(self.training_path):
            try:
                with open(self.training_path, 'r', encoding='utf-8') as f:
                    self.training = json.load(f)
            except Exception:
                self.training = {}
        else:
            self.training = {}

    def _match_by_role_or_category(self, prompt: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pure NLP-based matching using parsed entities and token similarity.
        No hardcoded rule-based logic - all matching based on:
        1. Parsed roles from NER model
        2. Parsed technologies/skills
        3. Token similarity with training keys
        
        Training data drives all behavior through:
        - additional_career_skills.json (NER training examples)
        - complete_training_data.json (complex prompt examples)
        - career_roadmap_training.json (career definitions)
        """
        prompt_lower = prompt.lower()
        
        # Extract parsed entities from NLP parser
        roles = parsed.get('parsed', {}).get('roles', []) or []
        technologies = parsed.get('parsed', {}).get('technologies', []) or []
        skills = parsed.get('parsed', {}).get('skills', []) or []
        categories = parsed.get('parsed', {}).get('categories', []) or []
        optional = parsed.get('parsed', {}).get('optional_skills', []) or []
        
        best_match = None
        best_match_score = 0
        
        logger.info(f"[NLP] Parsed entities - Roles: {roles}, Tech: {technologies}, Skills: {skills}")
        
        # Strategy 1: Exact match on parsed roles against training keys
        all_entities = roles + skills + technologies + categories + optional
        for entity in all_entities:
            entity_lower = entity.lower()
            for training_key in self.training.keys():
                if entity_lower == training_key.lower():
                    logger.info(f"[NLP] Exact match: '{entity}' → '{training_key}'")
                    return self.training[training_key]
        
        # Strategy 2: Substring match for parsed roles in training keys
        for entity in all_entities:
            entity_lower = entity.lower()
            if len(entity_lower) > 3:  # Avoid very short matches
                for training_key in self.training.keys():
                    tk_lower = training_key.lower()
                    if entity_lower in tk_lower or tk_lower in entity_lower:
                        match_score = len(entity_lower) * 10
                        if match_score > best_match_score:
                            best_match = training_key
                            best_match_score = match_score
                            logger.info(f"[NLP] Substring match: '{entity}' in '{training_key}' (score: {match_score})")
        
        # Strategy 3: Technology matching with training entry tech lists
        for tech in technologies:
            tech_lower = tech.lower()
            for training_key, training_entry in self.training.items():
                entry_techs = [t.lower() for t in (training_entry.get('technologies') or [])]
                if tech_lower in entry_techs:
                    match_score = 100
                    if match_score > best_match_score:
                        best_match = training_key
                        best_match_score = match_score
                        logger.info(f"[NLP] Tech match: '{tech}' found in {training_key}")
        
        # Strategy 4: Multi-skill matching (e.g., Python + Django → django developer)
        if len(skills) > 1:
            skill_matches = {}
            for training_key, training_entry in self.training.items():
                tk_lower = training_key.lower()
                entry_techs = [t.lower() for t in (training_entry.get('technologies') or [])]
                entry_skills = [s.lower() for s in (training_entry.get('core_skills') or [])]
                
                all_training_content = tk_lower + ' ' + ' '.join(entry_techs) + ' ' + ' '.join(entry_skills)
                skill_matches_count = sum(1 for skill in skills if skill.lower() in all_training_content)
                
                if skill_matches_count > 0:
                    skill_matches[training_key] = skill_matches_count
            
            if skill_matches:
                best_multi = max(skill_matches, key=skill_matches.get)
                if skill_matches[best_multi] >= 2:
                    logger.info(f"[NLP] Multi-skill match: {skill_matches[best_multi]} skills → {best_multi}")
                    return self.training[best_multi]
        
        # Strategy 5: Token-based similarity (word overlap, order-insensitive)
        # This allows "sql database engineer" to match "sql engineer"
        def _tokens(text: str):
            return set(re.findall(r"\w+", text.lower()))
        
        prompt_tokens = _tokens(prompt_lower)
        
        for training_key in self.training.keys():
            key_tokens = _tokens(training_key)
            if not key_tokens:
                continue
            
            # Intersection score
            intersection = len(key_tokens & prompt_tokens)
            union = len(key_tokens | prompt_tokens)
            jaccard_similarity = intersection / union if union > 0 else 0
            
            # If all key tokens are in prompt (superset match), high score
            if key_tokens.issubset(prompt_tokens):
                match_score = 200
            # If good token overlap (>50%), score by overlap count
            elif intersection >= 2:
                match_score = intersection * 20
            else:
                match_score = jaccard_similarity * 50
            
            if match_score > best_match_score:
                best_match = training_key
                best_match_score = match_score
        
        # Strategy 6: Category-based matching from tech dictionary
        if categories:
            for category in categories:
                cat_lower = category.lower()
                for training_key, training_entry in self.training.items():
                    entry_techs = [t.lower() for t in (training_entry.get('technologies') or [])]
                    entry_skills = [s.lower() for s in (training_entry.get('core_skills') or [])]
                    
                    if any(cat_lower in tech for tech in entry_techs) or any(cat_lower in skill for skill in entry_skills):
                        match_score = 80
                        if match_score > best_match_score:
                            best_match = training_key
                            best_match_score = match_score
                            logger.info(f"[NLP] Category match: '{category}' → {training_key}")
        
        if best_match and best_match_score > 0:
            logger.info(f"[NLP] Final match: {best_match} (score: {best_match_score})")
            return self.training[best_match]

        # Last fallback: return generic learning roadmap if available
        logger.info(f"[NLP] No match found, returning generic roadmap")
        return self.training.get('generic', {})

    def generate_roadmap(self, prompt: str) -> Dict[str, Any]:
        if not prompt or not prompt.strip():
            return {'error': 'Empty prompt'}

        parsed = self.parser.parse_query(prompt)

        matched = self._match_by_role_or_category(prompt, parsed)

        # Separate mandatory (core_skills + technologies) from optional
        core_skills = matched.get('core_skills', [])
        technologies = matched.get('technologies', [])
        optional_skills = matched.get('optional_skills', [])
        
        # Build recommended skills: core + technologies (mandatory), then optional
        mandatory_skills = core_skills + technologies
        
        # Build roadmap output with clear categorization
        roadmap = {
            'original_prompt': prompt,
            'matched_profile': matched.get('role', 'Generic'),
            'recommended_skills': mandatory_skills,
            'optional_skills': optional_skills,
            'mandatory_skills_count': len(mandatory_skills),
            'optional_skills_count': len(optional_skills),
            'learning_path': matched.get('learning_path', []),
            'projects': matched.get('projects', []),
            'timeline_weeks': matched.get('timeline_weeks', None),
            'effort_per_week': matched.get('effort_per_week', ''),
            'prerequisite_skills': matched.get('prerequisite_skills', []),
            'career_path': matched.get('career_path', ''),
            'job_market': matched.get('job_market', ''),
            'salary_range_usd': matched.get('salary_range_usd', ''),
            'notes': matched.get('notes', ''),
            'parsed': parsed.get('parsed', {})
        }

        # De-duplicate recommended_skills while preserving order
        seen = set()
        dedup_skills = []
        for s in roadmap['recommended_skills']:
            key = s.lower()
            if key not in seen:
                seen.add(key)
                dedup_skills.append(s)
        roadmap['recommended_skills'] = dedup_skills

        # De-duplicate optional_skills while preserving order
        seen = set([s.lower() for s in dedup_skills])
        dedup_optional = []
        for s in roadmap['optional_skills']:
            key = s.lower()
            if key not in seen:
                seen.add(key)
                dedup_optional.append(s)
        roadmap['optional_skills'] = dedup_optional
        
        # Add technologies section for job market matching
        roadmap['technologies'] = technologies
        roadmap['technologies_count'] = len(technologies)
        
        # Add section for job requirements matching (stub for integration with requirements API)
        roadmap['job_requirements_matching'] = {
            'description': 'These skills can be matched against open job requirements',
            'core_skills_for_matching': core_skills,
            'how_to_use': 'Send core_skills to /requirements endpoint to find matching open positions',
            'integration_endpoint': '/api/requirements/match',
            'sample_call': f'POST /api/requirements/match with body: {{"core_skills": {core_skills[:3]}}}',
            'expected_response': 'Array of job requirements where >= 70% of core_skills are required'
        }
        
        return roadmap
    
    def get_matching_requirements_by_skills(self, core_skills: List[str]) -> Dict[str, Any]:
        """
        Helper method to prepare skill list for requirement matching.
        Returns structured data for passing to requirements API call.
        
        Core skills should be matched against job requirements where:
        - At least 70% of core_skills appear in requirement skills
        - Requirements are marked as 'Open' or 'Active'
        - Return matched requirements sorted by skill match percentage
        """
        if not core_skills:
            return {
                'core_skills': [],
                'matching_requirements': [],
                'total_matches': 0,
                'message': 'No core skills provided'
            }
        
        # Normalize skills for comparison
        normalized_skills = [skill.lower().strip() for skill in core_skills]
        
        return {
            'core_skills': core_skills,
            'normalized_skills': normalized_skills,
            'total_core_skills': len(core_skills),
            'matching_requirements': [],
            'total_matches': 0,
            'minimum_match_percentage': 70,
            'note': 'Call C# Requirements API with these core_skills to fetch matching job openings'
        }

    def get_all_skills(self) -> Dict[str, Any]:
        """Return all available skills/technologies from tech dictionary"""
        all_skills = []
        
        # Collect from all categories
        for category_data in self.parser.tech_categories.values():
            techs = category_data.get('technologies', [])
            all_skills.extend(techs)
        
        # De-duplicate while preserving order
        seen = set()
        unique_skills = []
        for skill in all_skills:
            key = skill.lower()
            if key not in seen:
                seen.add(key)
                unique_skills.append(skill)
        
        return {
            'total_skills': len(unique_skills),
            'skills': sorted(unique_skills),
            'categories': list(self.parser.tech_categories.keys())
        }


# Singleton
_service_instance = None


def get_roadmap_service():
    global _service_instance
    if _service_instance is None:
        _service_instance = CareerRoadmapService()
    return _service_instance
