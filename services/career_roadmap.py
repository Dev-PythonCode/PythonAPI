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
        Intelligently match user prompt to training data roadmap.
        Uses multiple strategies in order of specificity.
        """
        prompt_lower = prompt.lower()
        
        # ⭐ ROLE NORMALIZATION: Treat role variants as standard roles
        # Convert "programmer" → "developer", "coder" → "developer"
        # This ensures "python programmer" matches "python developer" career path
        role_normalizations = {
            'programmer': 'developer',
            'coder': 'developer',
            'engineer': 'engineer'
        }
        
        for role_variant, normalized_role in role_normalizations.items():
            prompt_lower = re.sub(r'\b' + role_variant + r'\b', normalized_role, prompt_lower)
        
        # ⭐ IMPLICIT TECHNOLOGY-TO-CAREER MAPPING
        # If prompt contains only technology keywords without explicit role, infer the career path
        # E.g., "Want to learn Azure" → assume "Cloud Engineer" or "Azure Cloud Engineer"
        tech_to_career = {
            'azure': 'cloud engineer',
            'aws': 'cloud engineer',
            'gcp': 'cloud engineer',
            'kubernetes': 'cloud engineer',
            'kubernetes': 'devops engineer',
            'docker': 'devops engineer',
            'terraform': 'devops engineer',
            'devops': 'devops engineer',
            'jenkins': 'devops engineer',
            'kafka': 'data engineer',
            'spark': 'data engineer',
            'hadoop': 'data engineer',
            'airflow': 'data engineer',
            'dbt': 'data engineer',
            'snowflake': 'data engineer',
            'redshift': 'data engineer',
            'bigquery': 'data engineer'
        }
        
        for tech_keyword, career_path in tech_to_career.items():
            if tech_keyword in prompt_lower and not any(role in prompt_lower for role in ['developer', 'engineer', 'architect', 'specialist', 'analyst']):
                # If tech keyword found and NO explicit role, inject the career path
                prompt_lower = prompt_lower + ' ' + career_path
                logger.info(f"✅ Implicit career mapping: '{tech_keyword}' → added '{career_path}' to prompt")
        
        # Strategy 1: Exact match on parsed roles
        roles = parsed.get('parsed', {}).get('roles', [])
        categories = parsed.get('parsed', {}).get('categories', [])
        skills = parsed.get('parsed', {}).get('skills', [])
        optional = parsed.get('parsed', {}).get('optional_skills', [])

        # Check if any parsed role exactly matches a training key
        all_parsed = roles + categories + skills + optional
        for parsed_item in all_parsed:
            for training_key in self.training.keys():
                if parsed_item.lower() == training_key.lower():
                    return self.training[training_key]
        
        # Strategy 2: Match by technology/skill keywords with high specificity
        # Prioritize matches with more overlapping words
        best_match = None
        best_match_score = 0
        best_match_strategy = ""
        
        # Strategy 2a: Direct keyword search in prompt for training keys
        for training_key in self.training.keys():
            if training_key.lower() in prompt_lower:
                return self.training[training_key]

        # Strategy 2a.5: Token-based, order-insensitive training key match
        # Handles prompts like "SQL Database engineer" matching "sql engineer"
        def _tokens(text: str):
            return set(re.findall(r"\w+", text.lower()))

        prompt_tokens = _tokens(prompt_lower)

        for training_key in self.training.keys():
            key_tokens = _tokens(training_key)
            if not key_tokens:
                continue

            # If all tokens of the training key appear in the prompt (any order), match.
            if key_tokens.issubset(prompt_tokens):
                return self.training[training_key]

            # If majority of tokens match (>=2) and at least one token is a technology/keyword, prefer it.
            if len(key_tokens & prompt_tokens) >= 2:
                return self.training[training_key]
        
        # Strategy 2b: Multi-skill matching - if multiple skills match, find the training key
        # that matches the most skills (e.g., Selenium + Python should match "selenium python")
        # DO THIS BEFORE individual skill matching to prioritize combinations
        if len(skills) > 1:
            multi_skill_matches = {}
            for training_key in self.training.keys():
                key_lower = training_key.lower()
                skill_overlap = sum(1 for skill in skills if skill.lower() in key_lower)
                if skill_overlap > 0:
                    multi_skill_matches[training_key] = skill_overlap
            
            if multi_skill_matches:
                best_multi_match = max(multi_skill_matches, key=multi_skill_matches.get)
                if multi_skill_matches[best_multi_match] >= 2:  # Require at least 2 skill matches
                    best_match = best_multi_match
                    best_match_score = 500  # Very high priority for multi-skill matches
                    best_match_strategy = f"Multi-skill match: {multi_skill_matches[best_multi_match]} skills"
                    return self.training[best_match]
        
        # Strategy 2c: Match skills found by parser with training key keywords
        if skills:
            for skill in skills:
                skill_lower = skill.lower()
                for training_key in self.training.keys():
                    key_lower = training_key.lower()
                    # Exact skill match in training key
                    if skill_lower == key_lower or skill_lower in key_lower:
                        match_score = len(skill_lower)  # Prioritize longer matches
                        if match_score > best_match_score:
                            best_match = training_key
                            best_match_score = match_score
                            best_match_strategy = f"Skill match: {skill}"
        
        # Strategy 2c-special: Handle React/Angular/Vue - these should lead to Frontend, not Backend
        if any(tech.lower() in ['react', 'angular', 'vue', 'angular.js', 'vue.js', 'typescript'] for tech in skills):
            # Check if frontend was also mentioned
            if 'frontend' in prompt_lower or any('frontend' in cat.lower() for cat in categories):
                best_match = 'frontend developer'
                best_match_score = 1000
                return self.training['frontend developer']

        # Strategy 2c-plus: Improved technology matching - check training entries for matching technologies
        # Get detected technologies from parser
        technologies_detected = []
        try:
            technologies_detected = parsed.get('parsed', {}).get('technologies', []) or []
        except Exception:
            technologies_detected = []
        
        # Combine with skills that might be technologies
        tech_candidates = []
        for t in technologies_detected + skills:
            t_lower = t.lower()
            # Check if this tech appears in any training entry's technologies or role name
            for training_key, training_entry in self.training.items():
                tk_lower = training_key.lower()
                entry_techs = [x.lower() for x in (training_entry.get('technologies') or [])]
                
                # Match if technology found in training key or technologies list
                if t_lower in tk_lower or t_lower in entry_techs:
                    # Score based on specificity (longer matches = better)
                    score = len(t_lower)
                    tech_candidates.append((training_key, training_entry, score, t))
        
        # Return the best technology match if found
        if tech_candidates:
            tech_candidates.sort(key=lambda x: x[2], reverse=True)
            best_tech_match = tech_candidates[0]
            logger.info(f"✅ Matched via technology detection: {best_tech_match[3]} → {best_tech_match[0]}")
            return best_tech_match[1]

        # Strategy: Prefer training entries that match detected programming languages/frameworks
        # e.g., if C# is detected and there is a "selenium csharp" entry prefer it
        # Build a list of detected technology tokens (parser stores languages in skills)
        technologies_detected = []
        try:
            technologies_detected = parsed.get('parsed', {}).get('technologies', []) or []
        except Exception:
            technologies_detected = []
        # include 'skills' which often contains language tokens (e.g., 'C#')
        technologies_detected = list(set([s.lower() for s in skills] + [t.lower() for t in technologies_detected]))

        if technologies_detected:
            # Prefer training entries that match BOTH detected skill (e.g., Selenium) and language (e.g., C#)
            # Separate detected languages from other skills
            language_tokens = {'c#', 'csharp', 'java', 'python', 'typescript'}
            detected_langs = [td for td in technologies_detected if td in language_tokens or td.replace('#','') in language_tokens]
            detected_nonlang = [sk.lower() for sk in skills if sk.lower() not in detected_langs]

            # First pass: prefer entries that match at least one non-language skill AND at least one language
            for training_key, training_entry in self.training.items():
                tk_lower = training_key.lower()
                entry_techs = [x.lower() for x in (training_entry.get('technologies') or [])]
                entry_core = [x.lower() for x in (training_entry.get('core_skills') or [])]

                nonlang_match = any(any(nl in item for item in entry_core + entry_techs + [tk_lower]) for nl in detected_nonlang) if detected_nonlang else False
                lang_match = any((ld in tk_lower) or (ld in entry_techs) or (ld.replace('#','') in tk_lower) for ld in detected_langs)

                if nonlang_match and lang_match:
                    return training_entry

            # Second pass: language-only fallback (e.g., general C# entry)
            for training_key, training_entry in self.training.items():
                tk_lower = training_key.lower()
                entry_techs = [x.lower() for x in (training_entry.get('technologies') or [])]
                if any(ld in tk_lower or ld in entry_techs or ld.replace('#','') in tk_lower for ld in detected_langs):
                    return training_entry
        
        # Strategy 2d: Match by word overlap (most common words should match first)
        prompt_words = prompt_lower.split()
        
        # Special handling for mobile platforms - must disambiguate between iOS and Android
        if 'ios' in prompt_lower or 'iphone' in prompt_lower or 'swift' in prompt_lower:
            if 'android' not in prompt_lower:
                best_match = 'ios developer'
                return self.training['ios developer']
        
        if 'android' in prompt_lower:
            if 'ios' not in prompt_lower and 'iphone' not in prompt_lower:
                best_match = 'android developer'
                return self.training['android developer']
        
        # Prioritize role keywords: build dynamically from tech dictionary and training keys
        # This avoids hardcoding and allows tuning via JSON files (`tech_dict_with_categories.json`, `career_roadmap_training.json`).
        role_keywords = {}

        # 1) Use category_search_patterns from tech dictionary if available (maps role phrases to categories)
        try:
            cat_patterns = self.parser.tech_dict.get('category_search_patterns', {}) if hasattr(self.parser, 'tech_dict') else {}
            for phrase, cats in cat_patterns.items():
                # Map each phrase to candidate training keys by looking for training entries that mention any of the target categories
                candidates = []
                for tk, entry in self.training.items():
                    entry_cats = []
                    # training entries may have 'technologies' or 'core_skills' we can match against category names
                    for c in cats:
                        if c.lower() in tk.lower() or any(c.lower() in (str(x).lower()) for x in (entry.get('technologies') or [])):
                            candidates.append(tk)
                if candidates:
                    role_keywords[phrase] = list(dict.fromkeys(candidates))
                else:
                    # fallback: map phrase to itself if there is a training key with same phrase
                    if phrase in self.training:
                        role_keywords[phrase] = [phrase]
        except Exception:
            pass

        # 2) Also derive simple keyword -> training_key mappings from existing training keys
        #    e.g., 'frontend developer' -> keywords 'frontend', 'developer'
        for tk in self.training.keys():
            tk_lower = tk.lower()
            parts = tk_lower.split()
            # add full phrase mapping
            role_keywords.setdefault(tk_lower, []).append(tk)
            # add each token mapping (single words)
            for p in parts:
                if len(p) > 2:  # avoid very short tokens
                    role_keywords.setdefault(p, []).append(tk)

        # Normalize lists (dedupe while preserving order)
        for k, v in list(role_keywords.items()):
            seen = set()
            dedup = []
            for item in v:
                if item not in seen:
                    dedup.append(item)
                    seen.add(item)
            role_keywords[k] = dedup

        # Evaluate role keywords against prompt
        for keyword, training_keys in role_keywords.items():
            if (keyword in prompt_words) or (keyword in prompt_lower):
                for training_key in training_keys:
                    if training_key in self.training:
                        match_score = 100 + len(keyword)
                        if match_score > best_match_score:
                            best_match = training_key
                            best_match_score = match_score
                            best_match_strategy = f"Role keyword: {keyword}"
        
        # Strategy 3: General word overlap matching
        if not best_match:
            for training_key in self.training.keys():
                key_words = training_key.lower().split()
                # Count how many words from training key appear in prompt
                overlap = sum(1 for kw in key_words if kw in prompt_words)
                if overlap > best_match_score:
                    best_match = training_key
                    best_match_score = overlap
                    best_match_strategy = f"Word overlap: {overlap}"
        
        if best_match and best_match_score > 0:
            return self.training[best_match]

        # Last fallback: return generic learning roadmap if available
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
        
        # Add note about matching open requirements
        roadmap['requirements_note'] = 'Use /requirements endpoint with core_skills to find matching job openings'

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
