import spacy
from spacy.tokens import Span
from spacy.language import Language
import re
import json
from pathlib import Path


class QueryParser:
    def __init__(self, spacy_model="en_core_web_sm"):
        self.nlp = spacy.load(spacy_model)
        self.load_skills_data()
        self.build_lookup_tables()
        self.setup_custom_ner()

    def load_skills_data(self):
        skills_path = Path(__file__).parent.parent / "data" / "skills.json"
        with open(skills_path, 'r') as f:
            data = json.load(f)
        self.skills_data = data['skills']
        self.locations = data['locations']
        self.availability_terms = data.get('availability_terms', {})
        self.skill_categories = data.get('skill_categories', {})

    def build_lookup_tables(self):
        """Build lookup tables for entity normalization"""

        # Skill lookup: alias -> canonical name
        self.skill_lookup = {}
        for skill in self.skills_data:
            canonical = skill['name']
            self.skill_lookup[canonical.lower()] = canonical
            for alias in skill.get('aliases', []):
                self.skill_lookup[alias.lower()] = canonical

        # Category lookup: category name -> list of skills
        self.category_to_skills = {}
        for skill in self.skills_data:
            category = skill.get('category', '').lower()
            if category:
                if category not in self.category_to_skills:
                    self.category_to_skills[category] = []
                self.category_to_skills[category].append(skill['name'])

        # Location lookup: variation -> canonical name
        self.location_lookup = {}
        for loc in self.locations:
            self.location_lookup[loc.lower()] = loc

        # Availability lookup: term -> canonical status
        self.availability_lookup = {}
        for status, terms in self.availability_terms.items():
            for term in terms:
                self.availability_lookup[term.lower()] = status

    def _analyze_experience_context(self, doc, skills, experience):
        """
        Determine if experience refers to skill-specific or total experience

        Args:
            doc: SpaCy Doc object
            skills: List of extracted skills
            experience: Extracted years of experience

        Returns:
            dict: {
                'type': 'skill_specific' or 'total',
                'skill': skill name if skill_specific, else None,
                'reason': explanation of detection
            }
        """
        if not experience or not skills:
            return {
                'type': 'total',
                'skill': None,
                'reason': 'No skills or experience found'
            }

        text_lower = doc.text.lower()

        # Pattern 1: Strong indicators - "X years [in/of/with] Skill"
        # These patterns strongly indicate skill-specific experience
        for skill in skills:
            skill_lower = skill.lower()

            skill_specific_patterns = [
                f"years in {skill_lower}",
                f"years of {skill_lower}",
                f"years with {skill_lower}",
                f"years {skill_lower}",
                f"{skill_lower} experience",
                f"experience in {skill_lower}",
                f"experience with {skill_lower}",
                f"{skill_lower} background",
                f"{skill_lower} expertise",
                f"having {skill_lower}",
                f"knowledge in {skill_lower}",
                f"knowledge of {skill_lower}",
                f"skilled in {skill_lower}",
                f"proficient in {skill_lower}"
            ]

            for pattern in skill_specific_patterns:
                if pattern in text_lower:
                    return {
                        'type': 'skill_specific',
                        'skill': skill,
                        'reason': f"Found pattern: '{pattern}'"
                    }

        # Pattern 2: Generic experience phrases - indicates TOTAL experience
        # These phrases indicate overall career experience, not skill-specific
        generic_patterns = [
            "years of experience",
            "years of professional experience",
            "years professional experience",
            "years in industry",
            "years of work",
            "years work experience",
            "total experience",
            "overall experience",
            "professional experience",
            "work experience",
            "industry experience",
            "career experience"
        ]

        for pattern in generic_patterns:
            if pattern in text_lower:
                return {
                    'type': 'total',
                    'skill': None,
                    'reason': f"Found generic pattern: '{pattern}'"
                }

        # Pattern 3: Proximity check
        # If experience number and skill name are very close, likely skill-specific
        experience_str = str(int(experience))

        for skill in skills:
            skill_lower = skill.lower()

            # Find positions of experience number and skill in text
            exp_match = re.search(r'\b' + re.escape(experience_str) + r'\b', text_lower)
            skill_match = re.search(r'\b' + re.escape(skill_lower) + r'\b', text_lower)

            if exp_match and skill_match:
                # Calculate character distance between them
                char_distance = abs(exp_match.start() - skill_match.start())

                # If very close (within 30 characters), likely skill-specific
                # Example: "5 years Python" or "Python 5 years"
                if char_distance <= 30:
                    return {
                        'type': 'skill_specific',
                        'skill': skill,
                        'reason': f"Experience and '{skill}' are {char_distance} chars apart (close proximity)"
                    }

        # Pattern 4: Position-based heuristic
        # If skill appears before "with X years", more likely total experience
        # If skill appears after "X years", more likely skill-specific
        experience_str = str(int(experience))

        for skill in skills:
            skill_lower = skill.lower()

            # Check if pattern is "Skill ... with X years" (total)
            pattern_skill_first = f"{skill_lower}.*with\\s*{experience_str}\\s*years"
            if re.search(pattern_skill_first, text_lower):
                # Check if there's a skill-specific indicator after
                remaining_text = text_lower[text_lower.find(experience_str):]
                if any(indicator in remaining_text for indicator in ["in", "of", "with"]):
                    continue  # Let other patterns handle it

                return {
                    'type': 'total',
                    'skill': None,
                    'reason': f"Pattern '{skill} with X years' suggests total experience"
                }

        # Default: When completely ambiguous, default to total experience
        # This is the safer assumption - users can refine if needed
        return {
            'type': 'total',
            'skill': None,
            'reason': 'Ambiguous query - defaulting to total experience (safer assumption)'
        }

    def setup_custom_ner(self):
        """Setup custom NER pipeline using trained patterns"""

        # Register custom attributes on Doc
        if not spacy.tokens.Doc.has_extension("extracted_skills"):
            spacy.tokens.Doc.set_extension("extracted_skills", default=[])
        if not spacy.tokens.Doc.has_extension("extracted_categories"):
            spacy.tokens.Doc.set_extension("extracted_categories", default=[])
        if not spacy.tokens.Doc.has_extension("extracted_location"):
            spacy.tokens.Doc.set_extension("extracted_location", default=None)
        if not spacy.tokens.Doc.has_extension("extracted_experience"):
            spacy.tokens.Doc.set_extension("extracted_experience", default=None)
        if not spacy.tokens.Doc.has_extension("extracted_availability"):
            spacy.tokens.Doc.set_extension("extracted_availability", default=None)
        if not spacy.tokens.Doc.has_extension("experience_operator"):
            spacy.tokens.Doc.set_extension("experience_operator", default="gte")
        if not spacy.tokens.Doc.has_extension("experience_context"):
            spacy.tokens.Doc.set_extension("experience_context", default=None)

        # Add custom entity recognizer
        if "custom_ner" not in self.nlp.pipe_names:
            # Need to capture self reference for use inside component
            parser_self = self

            @Language.component("custom_ner")
            def custom_ner_component(doc):
                text_lower = doc.text.lower()

                # Extract skills using lookup
                extracted_skills = []
                for term, canonical in parser_self.skill_lookup.items():
                    pattern = r'\b' + re.escape(term) + r'\b'
                    if re.search(pattern, text_lower):
                        if canonical not in extracted_skills:
                            extracted_skills.append(canonical)

                # Extract categories (cloud, frontend, backend, etc.)
                extracted_categories = []
                category_keywords = {
                    'cloud': ['cloud', 'aws', 'azure', 'gcp'],
                    'frontend': ['frontend', 'front-end', 'front end', 'ui'],
                    'backend': ['backend', 'back-end', 'back end', 'server'],
                    'devops': ['devops', 'dev-ops', 'dev ops', 'infrastructure'],
                    'databases': ['database', 'db', 'sql', 'nosql'],
                    'data science': ['data science', 'ml', 'machine learning', 'ai', 'artificial intelligence']
                }

                for category, keywords in category_keywords.items():
                    for keyword in keywords:
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        if re.search(pattern, text_lower):
                            if category not in extracted_categories:
                                extracted_categories.append(category)
                            break

                # Extract location using lookup
                extracted_location = None
                for term, canonical in parser_self.location_lookup.items():
                    pattern = r'\b' + re.escape(term) + r'\b'
                    if re.search(pattern, text_lower):
                        extracted_location = canonical
                        break

                # Extract availability using lookup
                extracted_availability = None
                sorted_terms = sorted(parser_self.availability_lookup.items(),
                                      key=lambda x: len(x[0]), reverse=True)
                for term, canonical in sorted_terms:
                    pattern = r'\b' + re.escape(term).replace(r'\ ', r'[\s-]?') + r'\b'
                    if re.search(pattern, text_lower):
                        extracted_availability = canonical
                        break

                # Extract experience with operator
                extracted_experience = None
                experience_operator = "gte"  # default: greater than or equal

                exp_patterns = [
                    # "above 5 years", "more than 5 years", "over 5 years", "greater than 5"
                    (r'(?:above|more\s+than|over|greater\s+than|>\s*)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', 'gt'),
                    # "at least 5 years", "minimum 5 years", "min 5 years"
                    (r'(?:at\s+least|minimum|min)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', 'gte'),
                    # "5+ years", "5 + years"
                    (r'(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)', 'gte'),
                    # "below 5 years", "less than 5 years", "under 5 years"
                    (r'(?:below|less\s+than|under|<\s*)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', 'lt'),
                    # "at most 5 years", "maximum 5 years"
                    (r'(?:at\s+most|maximum|max)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', 'lte'),
                    # "exactly 5 years", "equal to 5 years"
                    (r'(?:exactly|equal\s+to|=\s*)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', 'eq'),
                    # "5 to 8 years", "5-8 years", "between 5 and 8 years"
                    (r'(?:between\s+)?(\d+(?:\.\d+)?)\s*(?:to|-|and)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', 'range'),
                    # "5 years experience", "5 years of experience", "with 5 years"
                    (r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|expertise|background)?', 'gte'),
                    (r'with\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', 'gte'),
                    (r'having\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', 'gte'),
                ]

                for pattern, operator in exp_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        if operator == 'range':
                            # For range, store as min value with gte operator
                            # The max value would need separate handling in your search logic
                            extracted_experience = float(match.group(1))
                            experience_operator = 'gte'
                        else:
                            extracted_experience = float(match.group(1))
                            experience_operator = operator
                        break

                # Analyze experience context (skill-specific vs total)
                if extracted_experience and extracted_skills:
                    experience_context = parser_self._analyze_experience_context(
                        doc,
                        extracted_skills,
                        extracted_experience
                    )
                else:
                    experience_context = {
                        'type': 'total',
                        'skill': None,
                        'reason': 'No experience or skills found - default to total'
                    }

                # Store all extracted entities in doc
                doc._.extracted_skills = extracted_skills
                doc._.extracted_categories = extracted_categories
                doc._.extracted_location = extracted_location
                doc._.extracted_experience = extracted_experience
                doc._.extracted_availability = extracted_availability
                doc._.experience_operator = experience_operator
                doc._.experience_context = experience_context

                return doc

            self.nlp.add_pipe("custom_ner", last=True)

    def expand_categories_to_skills(self, categories):
        """Expand category names to actual skill names"""
        expanded_skills = []
        for category in categories:
            if category in self.category_to_skills:
                expanded_skills.extend(self.category_to_skills[category])
        return expanded_skills

    def parse_query(self, query):
        """
        Parse natural language query using SpaCy NER

        Args:
            query (str): Natural language query

        Returns:
            dict: Parsed query components including skills, experience context,
                  location, availability, and applied filters
        """
        doc = self.nlp(query)

        # Extract all entities from doc
        skills = doc._.extracted_skills
        categories = doc._.extracted_categories
        experience = doc._.extracted_experience
        experience_operator = doc._.experience_operator
        experience_context = doc._.experience_context
        location = doc._.extracted_location
        availability = doc._.extracted_availability

        # Expand categories to skills
        category_skills = self.expand_categories_to_skills(categories)

        # Build filters description for display
        filters = []

        if skills:
            filters.append(f"Skills: {', '.join(skills)}")

        if categories:
            filters.append(f"Categories: {', '.join(categories)}")

        if experience:
            # Operator descriptions
            op_text = {
                'gt': 'greater than',
                'gte': 'at least',
                'lt': 'less than',
                'lte': 'at most',
                'eq': 'exactly',
                'range': 'between'
            }.get(experience_operator, 'at least')

            # Add context to description
            if experience_context and experience_context['type'] == 'skill_specific':
                exp_desc = f"Experience: {op_text} {experience} years in {experience_context['skill']}"
            else:
                exp_desc = f"Experience: {op_text} {experience} years (total career)"

            filters.append(exp_desc)

        if location:
            filters.append(f"Location: {location}")

        if availability:
            filters.append(f"Availability: {availability}")

        # Return comprehensive parsed result
        return {
            'original_query': query,
            'parsed': {
                'skills': skills,
                'categories': categories,
                'category_skills': category_skills,
                'min_years_experience': experience,
                'experience_operator': experience_operator,
                'experience_context': experience_context,
                'location': location,
                'availability_status': availability
            },
            'applied_filters': filters,
            'skills_found': len(skills),
            'entities_detected': {
                'skills': skills,
                'categories': categories,
                'category_skills': category_skills,
                'location': location,
                'experience': experience,
                'experience_operator': experience_operator,
                'experience_context': experience_context,
                'availability': availability
            }
        }


# Test function for development/debugging
def test_query_parser():
    """Test the query parser with various queries"""
    parser = QueryParser()

    test_queries = [
        # Skill-specific experience
        "Find Python developers with 5 years in Python",
        "Python developer having 5 years Python experience",
        "Need AWS expert with 3+ years of AWS experience",
        "Java programmer with 6 years Java background",

        # Total experience
        "Find Python developers with 10 years of experience",
        "Senior developer with 15 years in industry",
        "Experienced professional with 8 years",

        # Ambiguous
        "Python developer with 5 years",
        "React expert having 4 years",

        # Complex queries
        "Python developer having good knowledge in Banking domain with 3+ years of experience",
        "Find cloud engineers in Bangalore with more than 5 years",
        "Senior Java developer with at least 8 years available full-time"
    ]

    print("=" * 80)
    print("QUERY PARSER TEST RESULTS")
    print("=" * 80)

    for query in test_queries:
        result = parser.parse_query(query)

        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print(f"{'=' * 80}")
        print(f"Skills: {result['parsed']['skills']}")
        print(f"Categories: {result['parsed']['categories']}")
        print(f"Experience: {result['parsed']['min_years_experience']} years")
        print(f"Experience Operator: {result['parsed']['experience_operator']}")

        if result['parsed']['experience_context']:
            ctx = result['parsed']['experience_context']
            print(f"Experience Type: {ctx['type']}")
            if ctx['skill']:
                print(f"Experience Skill: {ctx['skill']}")
            print(f"Detection Reason: {ctx['reason']}")

        print(f"Location: {result['parsed']['location']}")
        print(f"Availability: {result['parsed']['availability_status']}")
        print(f"\nApplied Filters:")
        for filter_desc in result['applied_filters']:
            print(f"  • {filter_desc}")


if __name__ == "__main__":
    # Run tests if file is executed directly
    test_query_parser()