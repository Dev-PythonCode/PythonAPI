# query_parser.py
# Natural Language Query Parser with SpaCy NER
# VERSION 3.0 - Added category detection and expansion for semantic search

import spacy
import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class QueryParser:
    def __init__(self):
        """Initialize the query parser with SpaCy model"""
        self.nlp = None
        self.tech_dict = {}
        self.tech_categories = {}  # ⭐ NEW: Category structure
        self.normalization_map = {}
        self.load_models()
        self.load_tech_dictionary()
        self.load_normalization_map()

    def load_models(self):
        """Load the trained SpaCy NER model"""
        model_path = "./models/talent_ner_model"

        if os.path.exists(model_path):
            print(f"[INFO] Loading SpaCy model from {model_path}")
            try:
                # Load model and remove unnecessary pipeline components to speed up parsing.
                self.nlp = spacy.load(model_path)
                # Keep only the components required for our use-case (NER). Remove others.
                keep = {"ner"}
                existing = list(self.nlp.pipe_names)
                for name in existing:
                    if name not in keep:
                        try:
                            self.nlp.remove_pipe(name)
                        except Exception:
                            # If removal fails, ignore and continue
                            pass

                print(f"[INFO] ✅ Model loaded successfully! (pipes: {self.nlp.pipe_names})")
                if "ner" in self.nlp.pipe_names:
                    print(f"[INFO] Entity types: {list(self.nlp.get_pipe('ner').labels)}")
            except Exception as e:
                print(f"[ERROR] ❌ Failed to load model: {e}")
                print(f"[INFO] Using blank English model as fallback")
                self.nlp = spacy.blank("en")
        else:
            print(f"[ERROR] ❌ Trained model not found at {model_path}")
            print(f"[ERROR] Please run: python train_spacy_model.py")
            print(f"[INFO] Using blank English model as fallback")
            self.nlp = spacy.blank("en")

    def load_tech_dictionary(self):
        """Load technology dictionary with categories"""
        dict_path = "./data/tech_dict_with_categories.json"

        if os.path.exists(dict_path):
            try:
                with open(dict_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tech_dict = data
                    # ⭐ NEW: Extract categories structure
                    self.tech_categories = data.get('categories', {})
                # Precompute known technologies and compiled regex patterns for faster lookups
                known_techs = []
                for category_data in self.tech_categories.values():
                    known_techs.extend(category_data.get('technologies', []))

                # Deduplicate and store lower-cased list
                # IMPORTANT: Sort by length (longest first) to match "JavaScript" before "Java"
                self.known_techs = list(dict.fromkeys(known_techs))
                self.known_techs.sort(key=len, reverse=True)
                
                self._tech_patterns = {}
                for tech in self.known_techs:
                    tech_lower = tech.lower()
                    # Use case-insensitive regex with proper word-boundary markers
                    try:
                        self._tech_patterns[tech] = re.compile(r'\b' + re.escape(tech_lower) + r'\b', re.I)
                    except re.error:
                        # Fallback to simple contains check using lowercased tech name
                        self._tech_patterns[tech] = None

                # Precompile role pattern for quick role detection
                self.role_keywords = ['developer', 'engineer', 'manager', 'architect', 'analyst', 'consultant']
                self._role_pattern = re.compile(r'\b(' + '|'.join(self.role_keywords) + r')s?\b', re.I)

                print(f"[INFO] ✅ Loaded tech dictionary with {len(self.tech_categories)} categories and {len(self.known_techs)} techs")
            except Exception as e:
                print(f"[ERROR] Failed to load tech dictionary: {e}")
                self.tech_dict = {}
                self.tech_categories = {}
        else:
            print(f"[WARNING] Tech dictionary not found at {dict_path}")
            self.tech_dict = {}
            self.tech_categories = {}

    def load_normalization_map(self):
        """Load normalization map for skill variants"""
        map_path = "./data/normalization_map.json"

        if os.path.exists(map_path):
            try:
                with open(map_path, 'r', encoding='utf-8') as f:
                    self.normalization_map = json.load(f)
                print(f"[INFO] ✅ Loaded {len(self.normalization_map)} normalization mappings")
            except Exception as e:
                print(f"[ERROR] Failed to load normalization map: {e}")
                self.normalization_map = {}
        else:
            print(f"[WARNING] Normalization map not found at {map_path}")
            self.normalization_map = {}

    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name using normalization map and remove requirement keywords"""
        skill_lower = skill.lower().strip()

        # Remove trailing requirement keywords
        requirement_keywords = ['mandatory', 'required', 'must have', 'essential', 'optional', 'nice to have', 'good to have', 'preferred', 'bonus', 'added advantage', 'not required']
        
        # Remove these keywords from the end of the skill name
        for keyword in requirement_keywords:
            if skill_lower.endswith(keyword):
                skill_lower = skill_lower[:-len(keyword)].strip()
                break

        if skill_lower in self.normalization_map:
            return self.normalization_map[skill_lower]

        return skill.strip()
    
    def expand_category(self, category: str) -> List[str]:
        """
        Expand a category to its constituent technologies
        
        ⭐ Uses tech_categories structure from JSON
        """
        category_lower = category.lower().strip()
        expanded_skills = []

        # Check new structure first
        for cat_name, cat_data in self.tech_categories.items():
            if cat_name.lower() == category_lower:
                return cat_data.get('technologies', [])
        
        # Fallback to old structure (if exists)
        for tech, info in self.tech_dict.items():
            if isinstance(info, dict) and 'category' in info:
                tech_category = info.get('category', '').lower()
                if tech_category == category_lower:
                    expanded_skills.append(tech)

        return expanded_skills

    def _extract_skills_from_keywords(self, query_lower: str) -> List[str]:
        """
        Fallback: Extract skills by keyword matching when SpaCy NER misses them
        (e.g., lowercase "angular" instead of "Angular")
        Also checks normalization map for typos/variants (e.g., "phyton"→Python, ".net"→C#)
        """
        found_skills = []
        
        # Common verb tokens to exclude (prevent "guide", "find", etc. being extracted as skills)
        verb_tokens = {'guide', 'find', 'show', 'list', 'want', 'search', 'help', 'suggest', 'need', 'recommend', 'tell', 'display'}

        # ⭐ NEW: Check normalization map for typos and variants first
        # Build lowercase version of normalization map for case-insensitive matching
        norm_map_lower = {k.lower(): v for k, v in self.normalization_map.items()}
        
        for typo_lower, canonical in norm_map_lower.items():
            # Use word boundary matching for alphanumeric-only patterns, but not for special chars like "."
            if re.match(r'^\w+$', typo_lower):  # Pure alphanumeric (e.g., "phyton", "reacct")
                pattern = re.compile(r'\b' + re.escape(typo_lower) + r'\b', re.I)
            else:  # Has special chars (e.g., ".net"), no word boundaries
                pattern = re.compile(re.escape(typo_lower), re.I)
            
            if pattern.search(query_lower):
                normalized = self.normalize_skill(canonical)  # Normalize the canonical form
                if normalized and normalized not in found_skills:
                    found_skills.append(normalized)
                    print(f"[INFO] 🔍 Found via normalization: '{typo_lower}'→'{normalized}'")

        # Use precompiled patterns for faster matching
        for tech, pattern in self._tech_patterns.items():
            if pattern is None:
                if tech.lower() in query_lower:
                    found_skills.append(tech)
                    print(f"[INFO] 🔍 Found skill via keyword match: {tech}")
            else:
                if pattern.search(query_lower):
                    found_skills.append(tech)
                    print(f"[INFO] 🔍 Found skill via keyword match: {tech}")

        # Filter out any matches that exactly correspond to verb tokens
        filtered_skills = []
        for skill in found_skills:
            if skill.lower() not in verb_tokens:
                filtered_skills.append(skill)
            else:
                print(f"[DEBUG] Skipping verb-like skill: '{skill}'")

        # ⭐ DEDUPLICATION: Remove skills that are substrings of other skills
        # Example: "SQL" is a substring of "SQL Server", so remove "SQL" if "SQL Server" exists
        # Also handle cases like "Java" vs "JavaScript" where one is a token within the other
        deduplicated_skills = []
        filtered_skills_lower = [s.lower() for s in filtered_skills]
        
        for i, skill in enumerate(filtered_skills):
            skill_lower = skill.lower()
            is_substring = False
            
            # Check if this skill is a substring of any other skill
            for j, other_skill in enumerate(filtered_skills):
                if i != j:  # Don't compare with itself
                    other_lower = other_skill.lower()
                    # Check if skill appears as a word within other_skill
                    if skill_lower in other_lower and len(other_lower) > len(skill_lower):
                        # Verify it's not just character overlap (e.g., "sql" vs "sqlalchemy")
                        # but rather a real word boundary
                        idx = other_lower.find(skill_lower)
                        if idx != -1:
                            # Check word boundary: either at start or after space/dash
                            before_ok = (idx == 0 or other_lower[idx-1] in ' -')
                            # Check end boundary: either at end or before space/dash
                            after_idx = idx + len(skill_lower)
                            after_ok = (after_idx >= len(other_lower) or other_lower[after_idx] in ' -')
                            
                            if before_ok and after_ok:
                                is_substring = True
                                print(f"[DEBUG] Skipping '{skill}' as it's a substring of '{other_skill}'")
                                break
                    
                    # ⭐ NEW: Also check if this skill's first word matches the other skill's first word
                    # Example: "Java" should be skipped if "JavaScript" exists (since "java" is the root)
                    skill_first_word = skill_lower.split()[0] if ' ' in skill_lower else skill_lower
                    other_first_word = other_lower.split()[0] if ' ' in other_lower else other_lower
                    
                    # If current skill is single-word and it's contained in the first word of a multi-word skill
                    if ' ' not in skill_lower and ' ' in other_lower:
                        if skill_lower in other_first_word or other_first_word.startswith(skill_lower):
                            is_substring = True
                            print(f"[DEBUG] Skipping '{skill}' as it's likely part of multi-word skill '{other_skill}'")
                            break
            
            if not is_substring:
                deduplicated_skills.append(skill)

        return deduplicated_skills

    def _deduplicate_conflicting_skills(self, skills: List[str]) -> List[str]:
        """
        Remove skills that are prefixes/substrings of other skills
        Example: Remove "Java" if "JavaScript" exists, remove "SQL" if "SQL Server" exists
        """
        if not skills:
            return skills
        
        deduplicated = []
        
        for i, skill in enumerate(skills):
            skill_lower = skill.lower()
            conflicts = False
            
            # Check if this skill is a prefix/substring of any other skill
            for j, other_skill in enumerate(skills):
                if i != j:
                    other_lower = other_skill.lower()
                    
                    # Skip if same skill
                    if skill_lower == other_lower:
                        continue
                    
                    # Check if skill is a prefix of other_skill (e.g., "Java" vs "JavaScript")
                    if other_lower.startswith(skill_lower) and len(other_lower) > len(skill_lower):
                        # Make sure there's a word boundary (not just partial match like "go" vs "golang")
                        next_char_idx = len(skill_lower)
                        if next_char_idx < len(other_lower):
                            next_char = other_lower[next_char_idx]
                            # Word boundary = space, dash, or continuation (like "Java" + "Script")
                            if next_char in ' -' or next_char.isalpha():
                                conflicts = True
                                print(f"[DEBUG] Final dedup: Removing '{skill}' as it's a prefix of '{other_skill}'")
                                break
                    
                    # Check if skill is a word within a multi-word skill (e.g., "SQL" in "SQL Server")
                    elif ' ' in other_lower:
                        words = other_lower.split()
                        if skill_lower in words:
                            conflicts = True
                            print(f"[DEBUG] Final dedup: Removing '{skill}' as it's a word in '{other_skill}'")
                            break
            
            if not conflicts:
                deduplicated.append(skill)

        return deduplicated

    def _detect_skill_operator(self, query: str, skills: List[str]) -> str:
        """
        Detect if skills are connected with OR operator
        Returns: 'OR' if OR operator found between skills, otherwise 'AND'
        
        Examples:
            "Python or JavaScript" → 'OR'
            "Python and JavaScript" → 'AND'
            "Python, JavaScript" → 'AND'
        """
        query_lower = query.lower()
        
        # Check for explicit OR keywords
        or_keywords = [' or ', ' OR ', '|']
        
        for keyword in or_keywords:
            if keyword in query:
                # Verify that OR is between skills, not random text
                # Simple heuristic: if we have 2+ skills and OR appears, assume it's skill OR
                if len(skills) >= 2:
                    print(f"[INFO] 🔀 Detected OR operator in query")
                    return 'OR'
        
        # Default to AND
        return 'AND'

    def _detect_categories_and_expand(self, query_lower: str, doc) -> Tuple[List[str], List[str]]:
        """
        ⭐ NEW: Detect technology categories in query and expand to specific skills
        
        IMPORTANT FIX: 
        - If a role-based keyword (developer, engineer, architect) is found BUT a specific technology 
          appears before it (within 15 chars), skip the role-based category expansion
        - Example: "Python developer" → only Python (not all programming languages)
        - Example: "Need a developer" → expands to all programming languages (no specific tech before)
        
        Args:
            query_lower: Lowercase query string
            doc: SpaCy doc object
            
        Returns:
            tuple: (detected_categories, category_skills)
        """
        detected_categories = []
        category_skills = []
        
        print(f"[DEBUG] Checking for categories in query: {query_lower}")
        
        # ⭐ FIX: Only detect categories if there are explicit category phrases
        # Explicit category phrases: "any X", "X skills", "X technology", "one or more X"
        # This prevents false matches when someone just mentions a technology name
        explicit_category_phrases = [
            r'\bany\s+\w+\s+(skill|technology|tool|platform|framework)',  # "any cloud platform"
            r'\b(one|more)\s+or\s+more\s+\w+\s+(skill|technology)',  # "one or more cloud technology"
            r'\b(database|cloud|frontend|backend|devops|mobile)\s+(expert|specialist)',  # "database expert"
        ]
        
        has_explicit_category_phrase = False
        for pattern in explicit_category_phrases:
            if re.search(pattern, query_lower):
                has_explicit_category_phrase = True
                print(f"[DEBUG] ✅ Found explicit category phrase matching: {pattern}")
                break
        
        # ⭐ If no explicit category phrases, skip keyword matching (only use category names/aliases)
        # This prevents "JavaScript 2.00 years" from matching "JavaScript Library" category
        use_keywords = has_explicit_category_phrase
        
        print(f"[DEBUG] use_keywords={use_keywords}, has_explicit_category_phrase={has_explicit_category_phrase}")
        
        # ⭐ FIX: Define role-based keywords that should skip expansion if preceded by a technology
        role_based_keywords = {'developer', 'programmer', 'engineer', 'architect', 'analyst', 'consultant'}
        
        # Get all known technologies to check for preceding tech matches
        known_techs = []
        # Add canonical tech names
        for tech_name, tech_info in self.tech_dict.items():
            known_techs.append(tech_name.lower())
            # Also add variants if tech_info is a dict
            if isinstance(tech_info, dict):
                variants = tech_info.get('variants', [])
                known_techs.extend([v.lower() for v in variants])
        
        # Also add all normalized tech keywords (from normalization_map values)
        for normalized_name in self.normalization_map.values():
            if normalized_name.lower() not in known_techs:
                known_techs.append(normalized_name.lower())
        
        # Check each category
        for category_name, category_data in self.tech_categories.items():
            category_name_lower = category_name.lower()
            keywords = category_data.get('keywords', [])
            aliases = category_data.get('aliases', [])
            technologies = category_data.get('technologies', [])
            # Check if category name is in query (use word boundaries and ensure it's not used as a verb)
            try:
                pattern_cat = re.compile(r"\b" + re.escape(category_name_lower) + r"\b")
            except re.error:
                pattern_cat = None

            cat_matched = False
            if pattern_cat:
                for m in pattern_cat.finditer(query_lower):
                    # map character span to doc tokens and skip if span corresponds to verb tokens
                    span = doc.char_span(m.start(), m.end(), alignment_mode='contract')
                    if span is not None:
                        if any(tok.pos_ in ('VERB', 'AUX') for tok in span):
                            # skip verb-like usages
                            continue
                    detected_categories.append(category_name)
                    category_skills.extend(technologies)
                    print(f"[INFO] 📂 Category detected: {category_name} (from category name)")
                    cat_matched = True
                    break

            if cat_matched:
                continue
            
            # Check aliases
            for alias in aliases:
                alias_lower = alias.lower()
                try:
                    pattern_alias = re.compile(r"\b" + re.escape(alias_lower) + r"\b")
                except re.error:
                    pattern_alias = None

                if pattern_alias:
                    for m in pattern_alias.finditer(query_lower):
                        span = doc.char_span(m.start(), m.end(), alignment_mode='contract')
                        if span is not None and any(tok.pos_ in ('VERB', 'AUX') for tok in span):
                            continue
                        detected_categories.append(category_name)
                        category_skills.extend(technologies)
                        print(f"[INFO] 📂 Category detected: {category_name} (from alias: '{alias}')")
                        break
                    if category_name in detected_categories:
                        break
            
            if category_name in detected_categories:
                continue
            
            # ⭐ Check keywords ONLY if there are explicit category phrases in the query
            # This prevents false matches like "JavaScript" matching "JavaScript Library" category
            if not use_keywords:
                print(f"[DEBUG] 🚫 Skipping keyword matching for '{category_name}' (no explicit category phrase)")
                continue
            
            # Check keywords (more lenient matching)
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Only match keywords of 4+ chars to avoid false positives
                if len(keyword_lower) >= 4:
                    try:
                        pattern_kw = re.compile(r"\b" + re.escape(keyword_lower) + r"\b")
                    except re.error:
                        pattern_kw = None

                    if pattern_kw:
                        for m in pattern_kw.finditer(query_lower):
                            span = doc.char_span(m.start(), m.end(), alignment_mode='contract')
                            if span is not None and any(tok.pos_ in ('VERB', 'AUX') for tok in span):
                                # skip matches where the keyword functions as a verb
                                continue
                            
                            # ⭐ FIX: Check if the keyword is actually a technology name in the category
                            # Example: "JavaScript" keyword in "JavaScript Library" category shouldn't expand
                            # when the query is "JavaScript 2.00 years mandatory"
                            keyword_is_tech_name = keyword_lower in [t.lower() for t in technologies]
                            if keyword_is_tech_name:
                                print(f"[DEBUG] 🚫 Skipping keyword '{keyword_lower}' as it's a technology name, not a category")
                                continue
                            
                            # ⭐ FIX: Check if this is a role-based keyword preceded by a specific technology
                            if keyword_lower in role_based_keywords:
                                # Check if a specific technology appears before this keyword
                                keyword_pos = m.start()
                                text_before_keyword = query_lower[:keyword_pos]
                                
                                # Check if any known tech appears in the 15 chars before the keyword
                                found_preceding_tech = False
                                for tech in known_techs:
                                    # Find the last occurrence of this tech before the keyword
                                    tech_pos = text_before_keyword.rfind(tech)
                                    if tech_pos != -1:
                                        # Check if this tech is within 15 chars before keyword
                                        if keyword_pos - tech_pos < 15:
                                            print(f"[DEBUG] 🚫 Skipping role-based keyword '{keyword_lower}' (preceded by tech '{tech}' at distance {keyword_pos - tech_pos})")
                                            found_preceding_tech = True
                                            break
                                
                                if found_preceding_tech:
                                    continue  # Skip this role-based category if a tech precedes it
                            
                            detected_categories.append(category_name)
                            category_skills.extend(technologies)
                            print(f"[INFO] 📂 Category detected: {category_name} (from keyword: '{keyword}')")
                            break
                        if category_name in detected_categories:
                            break
        
        # Remove duplicates
        detected_categories = list(dict.fromkeys(detected_categories))  # Preserves order
        category_skills = list(dict.fromkeys(category_skills))
        
        print(f"[INFO] 📊 Categories found: {detected_categories}")
        print(f"[INFO] 📊 Category skills expanded: {len(category_skills)} skills")
        
        return detected_categories, category_skills

    def _detect_optional_skills(self, query: str) -> List[str]:
        """
        Extract sections that contain optional/nice-to-have keywords.
        Returns: List of text sections marked as optional
        """
        optional_keywords = [
            r'added advantage',
            r'nice to have',
            r'good to have',
            r'bonus',
            r'preferred',
            r'optional',
        ]
        
        optional_sections = []
        query_lower = query.lower()
        
        for keyword in optional_keywords:
            if keyword in query_lower:
                # Find the start: look for comma before the keyword or beginning
                idx = query_lower.find(keyword)
                start = query_lower.rfind(',', 0, idx)
                if start == -1:
                    start = 0
                else:
                    start += 1
                
                # Find the end: look for comma after the keyword or end
                end = query_lower.find(',', idx)
                if end == -1:
                    end = len(query)
                
                section = query[start:end].strip()
                if section and section not in optional_sections:
                    optional_sections.append(section)
        
        return optional_sections

    def _detect_mandatory_skills(self, query: str) -> List[str]:
        """
        Extract sections that contain mandatory keywords.
        Returns: List of text sections marked as mandatory
        """
        mandatory_keywords = [
            r'mandatory',
            r'required',
            r'must have',
            r'essential',
        ]
        
        mandatory_sections = []
        query_lower = query.lower()
        
        for keyword in mandatory_keywords:
            if keyword in query_lower:
                # Find the start: look for comma before the keyword or beginning
                idx = query_lower.find(keyword)
                start = query_lower.rfind(',', 0, idx)
                if start == -1:
                    start = 0
                else:
                    start += 1
                
                # Find the end: look for comma after the keyword or end
                end = query_lower.find(',', idx)
                if end == -1:
                    end = len(query)
                
                section = query[start:end].strip()
                if section and section not in mandatory_sections:
                    mandatory_sections.append(section)
        
        return mandatory_sections

    def _determine_skill_type(self, query: str, end_pos: int) -> str:
        """
        Determine if a skill is mandatory or optional based on keywords after its position.
        Handles multiple skills by finding the next comma or end of string.
        
        Key logic:
        - Only looks at text between current position and next comma/clause boundary
        - Defaults to 'mandatory' if no explicit keyword found
        - Does not look beyond clause boundaries
        
        Returns: 'mandatory', 'optional', or 'unknown'
        """
        query_lower = query.lower()
        
        # Find the next comma or 'and' after the skill to define clause boundary
        next_comma = query_lower.find(',', end_pos)
        next_and = query_lower.find(' and ', end_pos)
        
        # Determine clause boundary
        clause_end = len(query)
        if next_comma != -1 and next_and != -1:
            # Both exist, use the nearest one
            clause_end = min(next_comma, next_and)
        elif next_comma != -1:
            clause_end = next_comma
        elif next_and != -1:
            clause_end = next_and
        
        # Only look within this clause
        window_text = query_lower[end_pos:clause_end]
        
        mandatory_keywords = ['mandatory', 'required', 'must have', 'essential']
        optional_keywords = ['optional', 'nice to have', 'good to have', 'preferred', 'bonus', 'added advantage', 'not required']
        
        # Check mandatory first
        for keyword in mandatory_keywords:
            if keyword in window_text:
                return 'mandatory'
        
        # Then optional
        for keyword in optional_keywords:
            if keyword in window_text:
                return 'optional'
        
        # If no keyword found, default to 'unknown' (will be handled by caller)
        return 'unknown'
        
        return 'unknown'

    def _extract_skill_requirements(self, query: str) -> Dict[str, str]:
        """
        Extract all skills and their requirement types (mandatory or optional) from the query.
        Builds a map of skill -> type by analyzing comma-separated clauses and 'and' separated parts.
        
        Handles multiple skills in different clauses with different requirement types.
        Supports comma-separated clauses and "and" separators when requirement keywords are present.
        
        Example: "Python 2 years mandatory, SQL Server 2 years optional, AWS 2 years optional"
        Example: "C# 2 years mandatory and AWS 2 years nice to have, JavaScript 2 years as optional"
        Example: "python mandatory java script nice to have"
        Returns: {'python': 'mandatory', 'sql': 'optional', 'aws': 'optional'}
        """
        skill_requirement_map = {}
        query_lower = query.lower()
        
        # ⭐ NEW APPROACH: Position-based skill classification
        # For each skill, find its position and check which requirement keywords come before/after it
        optional_keywords = ['optional', 'nice to have', 'good to have', 'preferred', 'bonus', 'added advantage', 'not required']
        mandatory_keywords = ['mandatory', 'required', 'must have', 'essential']
        
        # Find positions of all requirement keywords
        keyword_positions = []
        for keyword in mandatory_keywords:
            pos = 0
            while True:
                pos = query_lower.find(keyword, pos)
                if pos == -1:
                    break
                keyword_positions.append((pos, keyword, 'mandatory'))
                pos += len(keyword)
        
        for keyword in optional_keywords:
            pos = 0
            while True:
                pos = query_lower.find(keyword, pos)
                if pos == -1:
                    break
                keyword_positions.append((pos, keyword, 'optional'))
                pos += len(keyword)
        
        # Sort by position
        keyword_positions.sort(key=lambda x: x[0])
        
        # For each known tech, find its position and determine requirement type
        # ⭐ IMPORTANT: Process skills by length (longest first) to match "JavaScript" before "Java"
        sorted_techs = sorted(self.known_techs, key=len, reverse=True)
        processed_positions = set()  # Track which positions we've already processed
        
        for tech in sorted_techs:
            tech_lower = tech.lower()
            
            # ⭐ Also check for common variants (e.g., "java script" for "javascript")
            tech_variants = [tech_lower]
            # Add spaced version for single-word techs (e.g., "javascript" → "java script")
            if ' ' not in tech_lower and len(tech_lower) > 4:
                # Check if we can split into reasonable words
                for i in range(3, len(tech_lower) - 2):
                    variant = tech_lower[:i] + ' ' + tech_lower[i:]
                    tech_variants.append(variant)
            
            # Find all occurrences of this tech in the query (trying all variants)
            for variant in tech_variants:
                pos = 0
                while True:
                    pos = query_lower.find(variant, pos)
                    if pos == -1:
                        break
                    
                    # Skip if this position overlaps with an already processed skill
                    end_pos = pos + len(variant)
                    if any(pos <= p < end_pos or p <= pos < p + 20 for p in processed_positions):
                        pos += 1
                        continue
                    
                    processed_positions.add(pos)
                    
                    # Determine requirement type based on nearest keyword
                    requirement_type = None
                    
                    # Look for keywords that come AFTER this skill first (more specific)
                    for kw_pos, kw_text, kw_type in keyword_positions:
                        if kw_pos > pos + len(variant):
                            # Check if keyword is within 30 characters after the skill
                            if (kw_pos - (pos + len(variant))) < 30:
                                # Check there's no other skill between this skill and the keyword
                                text_between = query_lower[pos + len(variant):kw_pos]
                                has_skill_between = False
                                for other_tech in sorted_techs:
                                    other_lower = other_tech.lower()
                                    if other_lower != tech_lower:
                                        # ⭐ FIX: Use word boundary check to avoid matching "R" in "yeaRs"
                                        # Check if other_tech appears as a complete word, not as part of another word
                                        if other_lower in text_between:
                                            # Find the position of other_tech in text_between
                                            idx = text_between.find(other_lower)
                                            if idx != -1:
                                                # Check word boundaries: before and after
                                                before_ok = (idx == 0 or not text_between[idx-1].isalnum())
                                                after_idx = idx + len(other_lower)
                                                after_ok = (after_idx >= len(text_between) or not text_between[after_idx].isalnum())
                                                
                                                if before_ok and after_ok:
                                                    has_skill_between = True
                                                    break
                                
                                if not has_skill_between:
                                    requirement_type = kw_type
                                    print(f"[DEBUG] Skill '{tech}' gets '{kw_type}' from keyword '{kw_text}' AFTER it")
                                    break
                    
                    # If no following keyword, look for keywords that come BEFORE this skill
                    if requirement_type is None:
                        for kw_pos, kw_text, kw_type in reversed(keyword_positions):
                            if kw_pos < pos:
                                # Check if keyword is within 50 characters before the skill
                                if pos - (kw_pos + len(kw_text)) < 50:
                                    # Check if the IMMEDIATELY preceding skill (if any) has been assigned this keyword already
                                    text_between = query_lower[kw_pos + len(kw_text):pos]
                                    
                                    # Only reject if there's a skill VERY close to the keyword (within 15 chars)
                                    has_close_skill = False
                                    for other_tech in sorted_techs:
                                        other_lower = other_tech.lower()
                                        if other_lower != tech_lower:
                                            other_pos = text_between.find(other_lower)
                                            if other_pos != -1 and other_pos < 15:
                                                has_close_skill = True
                                                break
                                    
                                    if not has_close_skill:
                                        requirement_type = kw_type
                                        print(f"[DEBUG] Skill '{tech}' gets '{kw_type}' from keyword '{kw_text}' BEFORE it")
                                        break
                
                    # Default to mandatory if no keyword found
                    if requirement_type is None:
                        requirement_type = 'mandatory'
                    
                    # Add to map
                    normalized = self.normalize_skill(tech)
                    normalized_lower = normalized.lower()
                    skill_requirement_map[normalized_lower] = requirement_type
                    
                    # Find the clause context for debugging
                    clause_start = max(0, pos - 30)
                    clause_end = min(len(query), pos + len(variant) + 30)
                    clause = query[clause_start:clause_end]
                    print(f"[INFO] 📋 Skill '{normalized_lower}' → '{requirement_type}' (clause: {clause}...)")
                    
                    # Move to next occurrence
                    pos += len(variant)
                    break  # Only process first occurrence of each skill
        
        return skill_requirement_map

    def _extract_locations(self, query: str, doc) -> List[str]:
        """
        Extract location names from query using:
        1. SpaCy GPE (Geo-Political Entity) extraction
        2. Keywords like "available in", "based in", "located in", "in"
        3. Common city/location names
        Handles multiple locations separated by "and", "or", ","
        """
        locations_found = []
        query_lower = query.lower()
        
        # Extended location list with Trivandrum, Manila, Colombo, Sri Lanka, Philippines
        common_locations = {
            'bangalore', 'bengaluru', 'mumbai', 'delhi', 'new delhi',
            'hyderabad', 'pune', 'chennai', 'kolkata', 'jaipur',
            'ahmedabad', 'surat', 'lucknow', 'chandigarh', 'indore',
            'kochi', 'coimbatore', 'vadodara', 'ludhiana', 'agra',
            'visakhapatnam', 'pimpri-chinchwad', 'patna', 'raipur',
            'trivandrum', 'thiruvananthapuram',
            'new york', 'london', 'san francisco', 'seattle', 'austin',
            'toronto', 'vancouver', 'singapore', 'dubai', 'sydney',
            'manila', 'colombo', 'sri lanka', 'philippines',
            'bay area', 'new york',
            'us', 'uk', 'usa', 'india', 'canada', 'remote', 'work from home'
        }
        
        # Extract from SpaCy GPE entities
        for ent in doc.ents:
            if ent.label_ in ('GPE', 'LOC', 'LOCATION'):
                loc = ent.text.strip()
                if loc.lower() not in [l.lower() for l in locations_found]:
                    locations_found.append(loc)
                    print(f"[INFO] 📍 Location detected (NER): {loc}")
        
        # Extract from keywords "available in", "based in", "located in", "can work in"
        # This pattern captures multiple locations separated by and/or/,
        location_patterns = [
            r'available\s+(?:in|at)\s+([A-Z][a-zA-Z\s,\-&]*?)(?:\s+(?:based|with|for|$|\.))',
            r'based\s+(?:in|at)\s+([A-Z][a-zA-Z\s,\-&]*?)(?:\s+(?:with|for|$|\.))',
            r'located\s+(?:in|at)\s+([A-Z][a-zA-Z\s,\-&]*?)(?:\s+(?:with|for|$|\.))',
            r'can\s+work\s+in\s+([A-Z][a-zA-Z\s,\-&]*?)(?:\s+(?:with|for|$|\.))',
            r'(?:in|available in)\s+([A-Z][a-zA-Z\s,\-&]*)(?:\s*(?:$|\.|\,))',
        ]
        
        for pattern in location_patterns:
            matches = re.finditer(pattern, query)
            for match in matches:
                loc_str = match.group(1).strip().rstrip(',').strip()
                if loc_str:
                    # Skip if this is likely availability text
                    availability_words = {'immediate', 'asap', 'urgently', 'temporary', 'support', 'contract'}
                    if any(word in loc_str.lower() for word in availability_words):
                        continue
                    
                    # Split by 'and', 'or', ','
                    split_locs = re.split(r'\s+(?:and|or)\s+|,\s*', loc_str)
                    for loc in split_locs:
                        loc = loc.strip()
                        if loc and len(loc) > 2 and loc.lower() not in [l.lower() for l in locations_found]:
                            locations_found.append(loc)
                            print(f"[INFO] 📍 Location detected (keyword): {loc}")
        
        # Extract common city names mentioned directly with multi-location support
        for city in common_locations:
            if city in query_lower:
                # Ensure it's a word boundary match
                pattern = r'\b' + re.escape(city) + r'\b'
                if re.search(pattern, query_lower):
                    # For multi-word locations like "Sri Lanka", "New York", etc.
                    if ' ' in city:
                        # Match the exact phrase
                        matches = re.finditer(re.escape(city), query_lower)
                        for match in matches:
                            original_text = query[match.start():match.end()]
                            if original_text.lower() not in [l.lower() for l in locations_found]:
                                locations_found.append(original_text)
                                print(f"[INFO] 📍 Location detected (common list): {original_text}")
                    else:
                        # For single-word cities, strip punctuation and find the word
                        for word in query.split():
                            word_clean = word.rstrip(',.;:!?')  # Remove trailing punctuation
                            if word_clean.lower() == city:
                                if word_clean.lower() not in [l.lower() for l in locations_found]:
                                    locations_found.append(word_clean)
                                    print(f"[INFO] 📍 Location detected (common list): {word_clean}")
                                break
        
        return locations_found
    
    def _detect_availability(self, query: str) -> Dict[str, Any]:
        """
        Detect employee availability status from query text.
        Maps keywords to database values: "Available", "Limited", "Not Available"
        Handles: immediate, ASAP, part-time, contract, support, etc.
        """
        query_lower = query.lower()
        availability_result = {
            "status": None,
            "keywords": [],
            "details": None
        }
        
        # Immediate availability keywords (Available)
        immediate_keywords = ['immediate', 'immediately', 'asap', 'urgently', 'urgent', 'right away', 'straight away']
        
        # Part-time/Limited availability keywords (Limited)
        limited_keywords = ['part time', 'part-time', 'part-timer', 'contract', 'freelance', 'support', 'temporarily', 
                           'limited support', 'limited availability', 'flexible', 'flexible hours']
        
        # Not available keywords (Not Available)
        unavailable_keywords = ['no availability', 'not available', 'unavailable', 'not immediately', 'cannot be available']
        
        # Check for immediate availability
        for keyword in immediate_keywords:
            if keyword in query_lower:
                availability_result["status"] = "Available"
                availability_result["keywords"].append(keyword)
                availability_result["details"] = "Immediate/ASAP"
                print(f"[INFO] ⏰ Availability detected (Immediate): {keyword}")
        
        # Check for limited/part-time availability (only if not already marked as Available)
        if availability_result["status"] != "Available":
            for keyword in limited_keywords:
                if keyword in query_lower:
                    availability_result["status"] = "Limited"
                    availability_result["keywords"].append(keyword)
                    availability_result["details"] = f"{keyword.title()} basis"
                    print(f"[INFO] ⏰ Availability detected (Limited): {keyword}")
                    break
        
        # Check for unavailable keywords (lowest priority)
        if availability_result["status"] is None:
            for keyword in unavailable_keywords:
                if keyword in query_lower:
                    availability_result["status"] = "Not Available"
                    availability_result["keywords"].append(keyword)
                    availability_result["details"] = "Currently unavailable"
                    print(f"[INFO] ⏰ Availability detected (Not Available): {keyword}")
                    break
        
        return availability_result

    def parse_query(self, query: str) -> Dict[str, Any]:
        if not query or not query.strip():
            return self._empty_result()

        query_lower = query.lower()
        doc = self.nlp(query)

        # ⭐ STEP 0.25: Detect availability status
        availability = self._detect_availability(query)

        # ⭐ STEP 0.5: Build skill requirement map from clause analysis
        skill_requirement_map = self._extract_skill_requirements(query)

        # ⭐ STEP 0.75: Extract locations (handles multiple locations with and/or/,)
        locations = self._extract_locations(query, doc)

        # ⭐ STEP 1: Detect categories
        detected_categories, category_skills = self._detect_categories_and_expand(query_lower, doc)

        # ⭐ STEP 2: Extract entities from SpaCy
        technologies = []
        optional_technologies = []
        tech_categories = []
        tech_experiences = []
        overall_experiences = []
        skill_levels = []
        roles = []
        certifications = []
        companies = []
        dates = []

        for ent in doc.ents:
            entity_text = ent.text.strip()
            
            # Skip entities that are verb tokens (imperative commands)
            verb_tokens = {'guide', 'find', 'show', 'list', 'want', 'search', 'help', 'suggest', 'need', 'recommend', 'tell', 'display', 'looking', 'seeking'}
            if entity_text.lower() in verb_tokens:
                print(f"[DEBUG] Skipping verb entity: '{entity_text}'")
                continue

            if ent.label_ == "TECHNOLOGY":
                # ⭐ FILTER: Reject entities that contain requirement keywords (model misclassifications)
                # Example: "script is optional" is not a valid technology
                requirement_keywords = ['mandatory', 'required', 'must have', 'essential', 'optional', 'nice to have', 'good to have', 'preferred', 'bonus', 'is mandatory', 'is optional', 'is required']
                contains_requirement = any(keyword in entity_text.lower() for keyword in requirement_keywords)
                
                if contains_requirement:
                    print(f"[DEBUG] ⛔ Rejecting invalid TECHNOLOGY entity containing requirement keyword: '{entity_text}'")
                    continue
                
                normalized = self.normalize_skill(entity_text)
                normalized_lower = normalized.lower()
                
                # Check skill requirement map first (clause-based analysis)
                if normalized_lower in skill_requirement_map:
                    requirement = skill_requirement_map[normalized_lower]
                    if requirement == 'mandatory':
                        if normalized not in technologies:
                            technologies.append(normalized)
                            print(f"[INFO] 🔶 Detected mandatory technology (from skill map): {normalized}")
                    elif requirement == 'optional':
                        if normalized not in optional_technologies:
                            optional_technologies.append(normalized)
                            print(f"[INFO] 🔷 Detected optional technology (from skill map): {normalized}")
                else:
                    # Fallback to position-based detection
                    skill_type = self._determine_skill_type(query, ent.end_char)
                    
                    if skill_type == 'mandatory':
                        if normalized not in technologies:
                            technologies.append(normalized)
                            print(f"[INFO] 🔶 Detected mandatory technology: {normalized}")
                    elif skill_type == 'optional':
                        if normalized not in optional_technologies:
                            optional_technologies.append(normalized)
                            print(f"[INFO] 🔷 Detected optional technology: {normalized}")
                    else:
                        # Default to mandatory if no keyword found
                        if normalized not in technologies:
                            technologies.append(normalized)
                            print(f"[INFO] 🔶 Detected technology (default mandatory): {normalized}")

            elif ent.label_ == "TECH_CATEGORY":
                if entity_text.lower() not in [c.lower() for c in tech_categories]:
                    tech_categories.append(entity_text)
                    expanded = self.expand_category(entity_text)
                    category_skills.extend(expanded)

            elif ent.label_ == "TECH_EXPERIENCE":
                tech_experiences.append(entity_text)

            elif ent.label_ == "OVERALL_EXPERIENCE":
                overall_experiences.append(entity_text)

            elif ent.label_ == "GPE":
                if entity_text not in locations:
                    locations.append(entity_text)

            elif ent.label_ == "SKILL_LEVEL":
                # Ignore entities that are actually verbs/imperatives (e.g., "find", "show")
                is_verb = False
                try:
                    # ent may be a span; check its root token POS
                    is_verb = getattr(ent.root, 'pos_', '').upper() == 'VERB' or getattr(ent.root, 'pos_', '').upper() == 'AUX'
                except Exception:
                    is_verb = False

                verb_tokens = {'find', 'show', 'list', 'want', 'want to', 'looking', 'search'}
                if entity_text.lower() in verb_tokens or is_verb:
                    # skip misclassified imperative verbs
                    print(f"[DEBUG] Ignoring verb-like SKILL_LEVEL entity: '{entity_text}'")
                else:
                    if entity_text not in skill_levels:
                        skill_levels.append(entity_text)

            elif ent.label_ == "ROLE":
                if entity_text not in roles:
                    roles.append(entity_text)

            elif ent.label_ == "CERTIFICATION":
                if entity_text not in certifications:
                    certifications.append(entity_text)

            elif ent.label_ == "ORG":
                if entity_text not in companies:
                    companies.append(entity_text)

            elif ent.label_ == "DATE":
                if entity_text not in dates:
                    dates.append(entity_text)

        # ⭐ STEP 2.5: Fallback keyword matching for case-insensitive skills
        keyword_skills = self._extract_skills_from_keywords(query_lower)
        
        # Find positions of optional keywords to help classify unmapped skills
        optional_keyword_positions = []
        optional_keywords = ['optional', 'nice to have', 'good to have', 'preferred', 'bonus', 'added advantage', 'not required']
        for keyword in optional_keywords:
            pos = query_lower.find(keyword)
            if pos != -1:
                optional_keyword_positions.append(pos)
        
        first_optional_keyword_pos = min(optional_keyword_positions) if optional_keyword_positions else len(query)
        
        for skill in keyword_skills:
            normalized = self.normalize_skill(skill)
            normalized_lower = normalized.lower()
            
            # ⭐ Check if this skill conflicts with existing skills (e.g., "Java" vs "JavaScript")
            conflicts_with_existing = False
            all_existing_skills = technologies + optional_technologies
            
            for existing_skill in all_existing_skills:
                existing_lower = existing_skill.lower()
                # Skip if single-word skill conflicts with multi-word skill containing it
                if ' ' not in normalized_lower and ' ' in existing_lower:
                    if normalized_lower in existing_lower.split()[0] or existing_lower.split()[0].startswith(normalized_lower):
                        conflicts_with_existing = True
                        print(f"[DEBUG] Skipping '{normalized}' as it conflicts with multi-word skill '{existing_skill}'")
                        break
                # Skip if multi-word skill conflicts with existing single-word skill
                elif ' ' in normalized_lower and ' ' not in existing_lower:
                    if existing_lower in normalized_lower.split()[0] or normalized_lower.split()[0].startswith(existing_lower):
                        # Remove the single-word skill in favor of the multi-word one
                        if existing_skill in technologies:
                            technologies.remove(existing_skill)
                            print(f"[DEBUG] Removing '{existing_skill}' in favor of multi-word skill '{normalized}'")
                        elif existing_skill in optional_technologies:
                            optional_technologies.remove(existing_skill)
                            print(f"[DEBUG] Removing '{existing_skill}' in favor of multi-word skill '{normalized}'")
            
            if conflicts_with_existing:
                continue
            
            if normalized not in technologies and normalized not in optional_technologies:
                # Check skill requirement map first
                if normalized_lower in skill_requirement_map:
                    requirement = skill_requirement_map[normalized_lower]
                    if requirement == 'mandatory':
                        technologies.append(normalized)
                        print(f"[INFO] 🔶 Detected mandatory technology (fallback from skill map): {normalized}")
                    elif requirement == 'optional':
                        optional_technologies.append(normalized)
                        print(f"[INFO] 🔷 Detected optional technology (fallback from skill map): {normalized}")
                else:
                    # For unmapped skills, check if skill appears before first optional keyword
                    skill_pos = query_lower.find(skill.lower())
                    
                    if skill_pos != -1:
                        # Smart classification: if skill appears before any "optional" keyword, it's mandatory
                        if skill_pos < first_optional_keyword_pos:
                            technologies.append(normalized)
                            print(f"[INFO] 🔶 Detected technology as mandatory (appears before 'optional'): {normalized}")
                        else:
                            # Skill appears after optional keyword, check the immediate context
                            skill_type = self._determine_skill_type(query, skill_pos + len(skill))
                            if skill_type == 'optional':
                                optional_technologies.append(normalized)
                                print(f"[INFO] 🔷 Detected optional technology (fallback): {normalized}")
                            else:
                                # Default to mandatory
                                technologies.append(normalized)
                                print(f"[INFO] 🔶 Detected technology (fallback default mandatory): {normalized}")
                    else:
                        # Couldn't find position, default to mandatory
                        technologies.append(normalized)
                        print(f"[INFO] 🔶 Detected technology (fallback default mandatory): {normalized}")

        # ⭐ STEP 2.6: Role keyword fallback - ensure roles like 'developer' are captured
        if hasattr(self, '_role_pattern') and self._role_pattern.search(query):
            # Find exact token in doc to preserve casing
            for token in doc:
                if token.text.lower().rstrip('s') in self.role_keywords and token.text not in roles:
                    roles.append(token.text)
                    print(f"[INFO] ✅ Added role from keyword fallback: {token.text}")
                    break

        # Clean up roles: remove entries that start with verbs/imperatives (misclassifications)
        cleaned_roles = []
        role_verb_prefixes = ('find', 'show', 'list', 'want', 'looking', 'search')
        for r in roles:
            if not r:
                continue
            low = r.lower().strip()
            if any(low.startswith(p + ' ') or low == p for p in role_verb_prefixes):
                print(f"[DEBUG] Removing misclassified role: '{r}'")
                continue
            cleaned_roles.append(r)

        # Deduplicate while preserving order
        seen = set()
        roles = []
        for r in cleaned_roles:
            key = r.lower()
            if key not in seen:
                seen.add(key)
                roles.append(r)

        # If no roles found but a role keyword exists in the query, add a canonical form
        if not roles and hasattr(self, '_role_pattern') and self._role_pattern.search(query_lower):
            m = self._role_pattern.search(query_lower)
            if m:
                kw = m.group(1)
                if kw:
                    roles.append(kw.capitalize())

        # ⭐ STEP 3: Merge categories and classify them as mandatory/optional
        # Deduplicate categories case-insensitively while preserving original case
        seen_categories = {}
        for cat in detected_categories + tech_categories:
            cat_lower = cat.lower()
            if cat_lower not in seen_categories:
                seen_categories[cat_lower] = cat
        all_categories = list(seen_categories.values())
        category_skills = list(dict.fromkeys(category_skills))
        
        # Classify categories based on skill requirement map
        mandatory_categories = []
        optional_categories = []
        
        for category in all_categories:
            category_lower = category.lower()
            
            # Check if any skill in this category was marked in the skill_requirement_map
            category_requirement = None
            for skill_lower, requirement in skill_requirement_map.items():
                # If a category name appears in requirement map, use that
                if category_lower == skill_lower:
                    category_requirement = requirement
                    break
            
            # If category not found in requirement map, check if it appears before optional keywords
            if category_requirement is None:
                optional_keyword_positions = []
                optional_keywords = ['optional', 'nice to have', 'good to have', 'preferred', 'bonus', 'added advantage', 'not required']
                for keyword in optional_keywords:
                    pos = query_lower.find(keyword)
                    if pos != -1:
                        optional_keyword_positions.append(pos)
                
                first_optional_keyword_pos = min(optional_keyword_positions) if optional_keyword_positions else len(query)
                category_pos = query_lower.find(category_lower)
                
                if category_pos != -1 and category_pos < first_optional_keyword_pos:
                    category_requirement = 'mandatory'
                elif 'optional' in query_lower or 'nice to have' in query_lower or 'good to have' in query_lower:
                    # If there are optional keywords and category appears after them, check context
                    category_requirement = 'optional'
                else:
                    category_requirement = 'mandatory'
            
            if category_requirement == 'mandatory':
                mandatory_categories.append(category)
            elif category_requirement == 'optional':
                optional_categories.append(category)

        # ⭐ STEP 4: Map experiences to specific skills
        skill_experience_map = self._map_experiences_to_skills(
            query,
            technologies,
            tech_experiences,
            overall_experiences
        )

        # Get global experience (for backward compatibility)
        global_min, global_max = self._extract_global_experience(tech_experiences, overall_experiences)
        exp_operator = self._extract_operator(query, tech_experiences, overall_experiences)

        # Determine global experience context
        experience_context = self._determine_experience_context(
            query,
            technologies,
            tech_experiences,
            overall_experiences
        )

        location = locations[0] if locations else None
        availability = self._detect_availability(query)

        # ⭐ DEDUPLICATION: Remove single-word skills that conflict with multi-word skills
        # Example: Remove "Java" if "JavaScript" exists
        technologies = self._deduplicate_conflicting_skills(technologies)
        optional_technologies = self._deduplicate_conflicting_skills(optional_technologies)
        
        # ⭐ CROSS-LIST DEDUPLICATION: Remove skills from one list if they conflict with skills in the other
        # Example: If "JavaScript" is in optional and "Java" is in mandatory, remove "Java"
        all_skills_for_check = technologies + optional_technologies
        combined_deduplicated = self._deduplicate_conflicting_skills(all_skills_for_check)
        
        # Rebuild lists keeping only non-conflicting skills
        technologies = [s for s in technologies if s in combined_deduplicated]
        optional_technologies = [s for s in optional_technologies if s in combined_deduplicated]

        # Build parsed result WITH CATEGORIES AND OPTIONAL SKILLS
        # Calculate mandatory_skills = technologies that are NOT in optional_technologies
        mandatory_skills = [skill for skill in technologies if skill not in optional_technologies]
        
        # ⭐ OR DETECTION: Check if skills are connected with OR operator (after mandatory_skills is calculated)
        skill_operator = self._detect_skill_operator(query, mandatory_skills)
        
        parsed_result = {
            'skills': technologies,
            'mandatory_skills': mandatory_skills,  # ⭐ FIXED: Added mandatory_skills field
            'optional_skills': optional_technologies,  # ⭐ NEW: Optional/nice-to-have skills
            'skill_operator': skill_operator,  # ⭐ NEW: 'AND' or 'OR' for skill matching
            'categories': all_categories,  # ⭐ Now includes detected categories
            'mandatory_categories': mandatory_categories,  # ⭐ NEW: Categories marked as mandatory
            'optional_categories': optional_categories,  # ⭐ NEW: Categories marked as optional
            'category_skills': category_skills,  # ⭐ Now includes expanded skills

            # Global experience (backward compatibility)
            'min_years_experience': global_min,
            'max_years_experience': global_max,
            'experience_operator': exp_operator,
            'experience_context': experience_context,

            # Per-skill experience requirements
            'skill_requirements': skill_experience_map,

            'location': location,
            'locations': locations,  # ⭐ All locations (handles multiple)
            'availability_status': availability,  # ⭐ Availability with status, keywords, details
            'skill_levels': skill_levels,
            'roles': roles,
            'certifications': certifications,
            'companies': companies,
            'dates': dates
        }

        # Build applied filters
        applied_filters = self._build_applied_filters(parsed_result)

        # ⭐ Calculate total skills (explicit + category)
        all_skills = list(dict.fromkeys(technologies + category_skills))

        return {
            'original_query': query,
            'parsed': parsed_result,
            'applied_filters': applied_filters,
            'skills_found': len(all_skills),  # ⭐ Total of explicit + category skills
            'entities_detected': {
                'skills': technologies,
                'optional_skills': optional_technologies,  # ⭐ Optional/nice-to-have skills
                'categories': all_categories,
                'mandatory_categories': mandatory_categories,  # ⭐ NEW: Mandatory categories
                'optional_categories': optional_categories,  # ⭐ NEW: Optional categories
                'category_skills': category_skills,
                'tech_experiences': tech_experiences,
                'overall_experiences': overall_experiences,
                'locations': locations,  # ⭐ All locations
                'primary_location': location,
                'availability': availability,  # ⭐ Full availability object
                'skill_levels': skill_levels,
                'roles': roles,
                'certifications': certifications,
                'companies': companies,
                'dates': dates
            }
        }

    def _map_experiences_to_skills(
            self,
            query: str,
            skills: List[str],
            tech_experiences: List[str],
            overall_experiences: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Map experience requirements to specific skills

        Example:
        Query: "Python with 2-5 years and AWS with 1 year"
        Returns: [
            {"skill": "Python", "min_years": 2, "max_years": 5, "operator": "between"},
            {"skill": "AWS", "min_years": 1, "max_years": None, "operator": "gte"}
        ]
        """
        skill_requirements = []
        query_lower = query.lower()

        for skill in skills:
            skill_lower = skill.lower()

            # Find experience mentions near this skill
            all_experiences = tech_experiences + overall_experiences

            for exp in all_experiences:
                exp_lower = exp.lower()

                # Check if this experience is associated with this skill
                skill_pos = query_lower.find(skill_lower)
                exp_pos = query_lower.find(exp_lower)

                if skill_pos != -1 and exp_pos != -1:
                    # If skill and experience are within 50 characters of each other
                    if abs(skill_pos - exp_pos) < 50:
                        # Check for connecting words
                        between_text = query_lower[min(skill_pos, exp_pos):max(skill_pos, exp_pos) + len(exp_lower)]

                        # Look for "with", "of", "in" patterns
                        if any(word in between_text for word in ['with', 'of', 'in', 'having']):
                            min_years, max_years = self._extract_year_range(exp)

                            if min_years:
                                operator = 'between' if max_years else 'gte'

                                skill_requirements.append({
                                    'skill': skill,
                                    'min_years': min_years,
                                    'max_years': max_years,
                                    'operator': operator,
                                    'experience_type': 'skill_specific'
                                })
                                break  # Found experience for this skill

        # If no specific mapping found, use global experience for all skills
        if not skill_requirements and (tech_experiences or overall_experiences):
            all_exp = tech_experiences + overall_experiences
            if all_exp:
                min_years, max_years = self._extract_year_range(all_exp[0])
                if min_years:
                    operator = 'between' if max_years else 'gte'
                    for skill in skills:
                        skill_requirements.append({
                            'skill': skill,
                            'min_years': min_years,
                            'max_years': max_years,
                            'operator': operator,
                            'experience_type': 'skill_specific'
                        })

        return skill_requirements

    def _extract_global_experience(self, tech_experiences: List[str], overall_experiences: List[str]) -> Tuple[
        Optional[float], Optional[float]]:
        """Extract global experience (for backward compatibility)"""
        # Use the FIRST experience mentioned
        all_exp = tech_experiences + overall_experiences
        if all_exp:
            return self._extract_year_range(all_exp[0])
        return (None, None)

    def _build_applied_filters(self, parsed_result: Dict) -> List[str]:
        """Build human-readable filter descriptions"""
        filters = []

        if parsed_result['skills']:
            filters.append(f"Skills: {', '.join(parsed_result['skills'])}")

        if parsed_result['categories']:
            filters.append(f"Categories: {', '.join(parsed_result['categories'])}")

        # Show per-skill requirements
        if parsed_result.get('skill_requirements'):
            for req in parsed_result['skill_requirements']:
                skill = req['skill']
                min_years = req['min_years']
                max_years = req.get('max_years')

                if max_years:
                    exp_text = f"{min_years}-{max_years} years"
                else:
                    exp_text = f"{min_years}+ years"

                filters.append(f"{skill}: {exp_text}")
        elif parsed_result['min_years_experience']:
            # Fallback to global experience
            if parsed_result['max_years_experience']:
                exp_text = f"{parsed_result['min_years_experience']}-{parsed_result['max_years_experience']} years"
            else:
                exp_text = f"{parsed_result['min_years_experience']}+ years"

            if parsed_result['experience_context'] and parsed_result['experience_context']['type'] == 'skill_specific':
                exp_text += f" in {parsed_result['experience_context']['skill']}"

            filters.append(f"Experience: {exp_text}")

        if parsed_result['location']:
            filters.append(f"Location: {parsed_result['location']}")

        if parsed_result['availability_status']:
            filters.append(f"Availability: {parsed_result['availability_status']}")

        return filters

    def _extract_year_range(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract year range from text

        Examples:
        - "2 to 5 years" → (2.0, 5.0)
        - "3-7 years" → (3.0, 7.0)
        - "5 years" → (5.0, None)
        - "5+ years" → (5.0, None)

        Returns: (min_years, max_years) tuple
        """
        # Pattern 1: "X to Y years" or "X-Y years"
        pattern1 = r'(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:year|yr)'
        match = re.search(pattern1, text.lower())

        if match:
            try:
                min_years = float(match.group(1))
                max_years = float(match.group(2))
                return (min_years, max_years)
            except ValueError:
                pass

        # Pattern 2: Single value "X years" or "X+ years"
        pattern2 = r'(\d+(?:\.\d+)?)\s*\+?\s*(?:year|yr)'
        match = re.search(pattern2, text.lower())

        if match:
            try:
                years = float(match.group(1))
                return (years, None)
            except ValueError:
                pass

        return (None, None)

    def _extract_years(self, tech_experiences: List[str], overall_experiences: List[str]) -> Tuple[
        Optional[float], Optional[float]]:
        """Extract numeric years from experience strings

        Returns: (min_years, max_years) tuple
        """
        # Try tech-specific experiences first
        for exp in tech_experiences:
            min_years, max_years = self._extract_year_range(exp)
            if min_years:
                return (min_years, max_years)

        # Fall back to overall experiences
        for exp in overall_experiences:
            min_years, max_years = self._extract_year_range(exp)
            if min_years:
                return (min_years, max_years)

        return (None, None)

    def _extract_operator(self, query: str, tech_experiences: List[str], overall_experiences: List[str]) -> str:
        """Determine experience operator"""
        query_lower = query.lower()
        all_experiences = tech_experiences + overall_experiences

        # Check for range patterns
        for exp in all_experiences:
            if 'to' in exp.lower() or '-' in exp:
                return 'between'  # Range operator

        # Check for explicit operators
        if any(phrase in query_lower for phrase in ['more than', 'greater than', 'over', 'above']):
            return 'gt'
        elif any(phrase in query_lower for phrase in ['at least', 'minimum', 'min']):
            return 'gte'
        elif any(phrase in query_lower for phrase in ['less than', 'under', 'below']):
            return 'lt'
        elif any(phrase in query_lower for phrase in ['at most', 'maximum', 'max']):
            return 'lte'
        elif any(phrase in query_lower for phrase in ['exactly', 'equal to']):
            return 'eq'

        # Check for + symbol
        for exp in all_experiences:
            if '+' in exp:
                return 'gte'

        return 'gte'

    def _determine_experience_context(
            self,
            query: str,
            skills: List[str],
            tech_experiences: List[str],
            overall_experiences: List[str]
    ) -> Optional[Dict[str, str]]:
        """
        Determine if experience is skill-specific or total

        IMPROVED: Better detection of "of Python" patterns
        """
        if not tech_experiences and not overall_experiences:
            return None

        query_lower = query.lower()

        # Check for explicit "of SKILL" or "in SKILL" patterns FIRST
        for skill in skills:
            skill_lower = skill.lower()

            # Pattern: "X years of Python experience"
            if f"of {skill_lower}" in query_lower:
                return {
                    'type': 'skill_specific',
                    'skill': skill,
                    'reason': f'Explicit "of {skill}" pattern detected'
                }

            # Pattern: "X years in Python"
            if f"in {skill_lower}" in query_lower:
                return {
                    'type': 'skill_specific',
                    'skill': skill,
                    'reason': f'Explicit "in {skill}" pattern detected'
                }

            # Pattern: "Python experience"
            if f"{skill_lower} experience" in query_lower:
                return {
                    'type': 'skill_specific',
                    'skill': skill,
                    'reason': f'"{skill} experience" pattern detected'
                }

            # Pattern: "experience with Python"
            if f"with {skill_lower}" in query_lower and "experience" in query_lower:
                return {
                    'type': 'skill_specific',
                    'skill': skill,
                    'reason': f'"experience with {skill}" pattern detected'
                }

        # If TECH_EXPERIENCE entity detected, it's skill-specific
        if tech_experiences:
            target_skill = skills[0] if skills else None
            return {
                'type': 'skill_specific',
                'skill': target_skill,
                'reason': 'TECH_EXPERIENCE entity detected by SpaCy'
            }

        # If only OVERALL_EXPERIENCE, it's total
        elif overall_experiences:
            return {
                'type': 'total',
                'skill': None,
                'reason': 'OVERALL_EXPERIENCE entity detected, no specific skill mentioned'
            }

        return None

    def _extract_availability(self, query: str) -> Optional[str]:
        """Extract availability status from query"""
        query_lower = query.lower()

        if any(word in query_lower for word in ['available', 'free', 'ready']):
            return 'Available'
        elif any(word in query_lower for word in ['limited', 'partial', 'part-time']):
            return 'Limited'
        elif any(word in query_lower for word in ['not available', 'busy', 'occupied']):
            return 'Not Available'

        return None

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'original_query': '',
            'parsed': {
                'skills': [],
                'mandatory_skills': [],  # ⭐ FIXED: Added mandatory_skills field
                'optional_skills': [],  # ⭐ Added optional_skills field
                'skill_operator': 'AND',  # ⭐ NEW: Default to AND
                'categories': [],
                'category_skills': [],
                'min_years_experience': None,
                'max_years_experience': None,
                'experience_operator': 'gte',
                'experience_context': None,
                'skill_requirements': [],
                'location': None,
                'availability_status': None,
                'skill_levels': [],
                'roles': [],
                'certifications': [],
                'companies': [],
                'dates': []
            },
            'applied_filters': [],
            'skills_found': 0,
            'entities_detected': {
                'skills': [],
                'categories': [],
                'category_skills': [],
                'tech_experiences': [],
                'overall_experiences': [],
                'location': None,
                'skill_levels': [],
                'roles': [],
                'certifications': [],
                'companies': [],
                'dates': []
            }
        }

    def get_entity_types(self) -> List[str]:
        """Get list of entity types the model can detect"""
        if self.nlp and 'ner' in self.nlp.pipe_names:
            return list(self.nlp.get_pipe('ner').labels)
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return {
            'model_loaded': self.nlp is not None,
            'entity_types': self.get_entity_types(),
            'tech_dict_size': len(self.tech_dict),
            'tech_categories': len(self.tech_categories),
            'normalization_mappings': len(self.normalization_map)
        }


# Singleton instance
_parser_instance = None


def get_parser() -> QueryParser:
    """Get or create QueryParser singleton instance"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = QueryParser()
    return _parser_instance