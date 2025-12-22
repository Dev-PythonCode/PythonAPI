import json
import os
from typing import Dict, Any, List

from services.query_parser import get_parser


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
        # Prefer explicit roles/skills/categories found by parser
        # 1. Check roles
        roles = parsed.get('parsed', {}).get('roles', [])
        categories = parsed.get('parsed', {}).get('categories', [])
        skills = parsed.get('parsed', {}).get('skills', [])
        optional = parsed.get('parsed', {}).get('optional_skills', [])

        # Lowercase sets for matching
        keys = set([r.lower() for r in roles] + [c.lower() for c in categories] + [s.lower() for s in skills] + [o.lower() for o in optional])

        # Exact match lookup in training data keys
        for key, entry in self.training.items():
            if key.lower() in keys:
                return entry

        # Fallback: keyword search in prompt
        prompt_lower = prompt.lower()
        for key, entry in self.training.items():
            if key.lower() in prompt_lower:
                return entry

        # Last fallback: return a generic learning roadmap if available
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

        return roadmap

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
