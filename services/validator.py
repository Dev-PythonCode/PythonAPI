class ApplicationValidator:
    def __init__(self):
        pass

    def calculate_query_match(self, employee_data, query_requirements):
        """
        Calculate match percentage based on search query requirements

        Args:
            employee_data: Dict with employee info including metadata and skills
            query_requirements: Parsed query requirements (skills, experience, location, etc.)

        Returns:
            Dict with match percentage and detailed breakdown
        """
        scores = {
            'skill_match': 0,
            'experience_match': 0,
            'location_match': 0,
            'availability_match': 0,
            'semantic_similarity': employee_data.get('similarity_score', 0)
        }

        weights = {
            'skill_match': 40,  # 40% weight
            'experience_match': 30,  # 30% weight
            'location_match': 10,  # 10% weight
            'availability_match': 10,  # 10% weight
            'semantic_similarity': 10  # 10% weight (from vector search)
        }

        total_weight = sum(weights.values())

        # Get employee metadata
        metadata = employee_data.get('metadata', {})
        emp_skills_str = metadata.get('skills', '')
        emp_skills = [s.strip() for s in emp_skills_str.split(',') if s.strip()]
        emp_location = metadata.get('location', '')
        emp_availability = metadata.get('availability', '')

        # Parse employee skill details from metadata if available
        # Note: You'll need to store years_of_experience in metadata or fetch from DB
        emp_skill_details = {}
        # For now, we'll work with what we have

        skill_analysis = []

        # 1. SKILL MATCHING (40%)
        required_skills = query_requirements.get('skills', [])
        if required_skills:
            matched_skills = 0
            for req_skill in required_skills:
                req_skill_lower = req_skill.lower()

                # Check if employee has this skill
                has_skill = any(req_skill_lower in emp_skill.lower() for emp_skill in emp_skills)

                if has_skill:
                    matched_skills += 1
                    skill_analysis.append({
                        'skill': req_skill,
                        'status': 'Match',
                        'employee_has': True
                    })
                else:
                    skill_analysis.append({
                        'skill': req_skill,
                        'status': 'Missing',
                        'employee_has': False
                    })

            # Calculate skill match percentage
            if required_skills:
                scores['skill_match'] = (matched_skills / len(required_skills)) * 100
        else:
            scores['skill_match'] = 100  # No skills required

        # 2. EXPERIENCE MATCHING (30%)
        experience_req = query_requirements.get('min_years_experience')
        experience_context = query_requirements.get('experience_context', {})

        if experience_req:
            # This is where experience context matters
            if experience_context.get('type') == 'skill_specific':
                # Need to check skill-specific experience
                # For now, we'll use a heuristic based on designation/seniority
                # In production, you'd fetch actual EmployeeSkills.YearsOfExperience from DB
                designation = metadata.get('designation', '').lower()

                # Heuristic mapping (you'll replace this with actual DB query)
                if 'senior' in designation or 'lead' in designation:
                    estimated_years = 7
                elif 'mid' in designation or 'intermediate' in designation:
                    estimated_years = 4
                else:
                    estimated_years = 2

                operator = query_requirements.get('experience_operator', 'gte')
                meets_requirement = self._check_experience_requirement(
                    estimated_years, experience_req, operator
                )

                if meets_requirement:
                    scores['experience_match'] = 100
                else:
                    # Partial credit
                    ratio = min(estimated_years / experience_req, 1.0) if experience_req > 0 else 1.0
                    scores['experience_match'] = ratio * 100

            elif experience_context.get('type') == 'total':
                # Check total career experience
                # Again, heuristic - replace with actual DB data
                designation = metadata.get('designation', '').lower()

                if 'senior' in designation or 'lead' in designation or 'principal' in designation:
                    estimated_total_years = 10
                elif 'mid' in designation or 'intermediate' in designation:
                    estimated_total_years = 5
                else:
                    estimated_total_years = 2

                operator = query_requirements.get('experience_operator', 'gte')
                meets_requirement = self._check_experience_requirement(
                    estimated_total_years, experience_req, operator
                )

                if meets_requirement:
                    scores['experience_match'] = 100
                else:
                    ratio = min(estimated_total_years / experience_req, 1.0) if experience_req > 0 else 1.0
                    scores['experience_match'] = ratio * 100
        else:
            scores['experience_match'] = 100  # No experience required

        # 3. LOCATION MATCHING (10%)
        required_location = query_requirements.get('location')
        if required_location:
            if emp_location.lower() == required_location.lower():
                scores['location_match'] = 100
            else:
                scores['location_match'] = 0
        else:
            scores['location_match'] = 100  # No location requirement

        # 4. AVAILABILITY MATCHING (10%)
        required_availability = query_requirements.get('availability_status')
        if required_availability:
            if emp_availability.lower() == required_availability.lower():
                scores['availability_match'] = 100
            elif emp_availability.lower() == 'available' and required_availability.lower() == 'limited':
                scores['availability_match'] = 100  # Available can work limited
            else:
                scores['availability_match'] = 0
        else:
            scores['availability_match'] = 100  # No availability requirement

        # Calculate weighted average
        total_score = sum(scores[key] * weights[key] / 100 for key in scores.keys())
        overall_percentage = (total_score / total_weight) * 100

        return {
            'overall_match_percentage': round(overall_percentage, 1),
            'component_scores': scores,
            'skill_analysis': skill_analysis,
            'experience_analysis': {
                'required': experience_req,
                'type': experience_context.get('type') if experience_context else 'total',
                'skill': experience_context.get('skill') if experience_context else None,
                'operator': query_requirements.get('experience_operator', 'gte'),
                'meets_requirement': scores['experience_match'] == 100
            },
            'location_match': scores['location_match'] == 100,
            'availability_match': scores['availability_match'] == 100,
            'weights_used': weights
        }

    def _check_experience_requirement(self, employee_years, required_years, operator):
        """Check if employee experience meets requirement based on operator"""
        if operator == 'gt':
            return employee_years > required_years
        elif operator == 'gte':
            return employee_years >= required_years
        elif operator == 'lt':
            return employee_years < required_years
        elif operator == 'lte':
            return employee_years <= required_years
        elif operator == 'eq':
            return employee_years == required_years
        else:
            return employee_years >= required_years  # Default to gte

    def calculate_skill_match(self, employee_skills, requirement_skills):
        """Calculate how well employee skills match requirement"""
        if not requirement_skills:
            return 100, []

        total_weight = sum(skill.get('weightage', 1) for skill in requirement_skills)
        earned_weight = 0
        skill_analysis = []

        # Create lookup for employee skills
        emp_skill_map = {s['skill_name'].lower(): s for s in employee_skills}

        for req_skill in requirement_skills:
            skill_name = req_skill['skill_name'].lower()
            min_years = req_skill.get('min_years_required', 0)
            weightage = req_skill.get('weightage', 1)
            is_mandatory = req_skill.get('is_mandatory', False)

            analysis = {
                'skill_name': req_skill['skill_name'],
                'required_years': min_years,
                'is_mandatory': is_mandatory,
                'status': 'Missing',
                'employee_years': 0,
                'score_contribution': 0
            }

            if skill_name in emp_skill_map:
                emp_skill = emp_skill_map[skill_name]
                emp_years = emp_skill.get('years_of_experience', 0)
                analysis['employee_years'] = emp_years

                if emp_years >= min_years:
                    analysis['status'] = 'Match'
                    analysis['score_contribution'] = weightage
                    earned_weight += weightage
                elif emp_years > 0:
                    # Partial credit
                    partial = (emp_years / min_years) * weightage if min_years > 0 else weightage
                    analysis['status'] = 'Partial'
                    analysis['score_contribution'] = partial
                    earned_weight += partial

            skill_analysis.append(analysis)

        match_percentage = (earned_weight / total_weight * 100) if total_weight > 0 else 0
        return round(match_percentage, 1), skill_analysis

    def get_recommendation(self, match_percentage, skill_analysis):
        """Generate AI recommendation based on match analysis"""
        # Check mandatory skills
        missing_mandatory = [s for s in skill_analysis
                             if s['is_mandatory'] and s['status'] == 'Missing']

        if missing_mandatory:
            return {
                'recommendation': 'Not recommended',
                'reason': f"Missing mandatory skills: {', '.join(s['skill_name'] for s in missing_mandatory)}",
                'suggested_action': 'Consider training or alternative candidates'
            }

        if match_percentage >= 80:
            return {
                'recommendation': 'Good fit',
                'reason': 'Candidate meets or exceeds all major skill requirements',
                'suggested_action': 'Proceed with interview'
            }
        elif match_percentage >= 60:
            partial_skills = [s for s in skill_analysis if s['status'] == 'Partial']
            return {
                'recommendation': 'Needs training',
                'reason': f"Good foundation but needs improvement in: {', '.join(s['skill_name'] for s in partial_skills[:3])}",
                'suggested_action': 'Consider with training plan'
            }
        else:
            missing_skills = [s for s in skill_analysis if s['status'] == 'Missing']
            return {
                'recommendation': 'Not recommended',
                'reason': f"Significant skill gaps: {', '.join(s['skill_name'] for s in missing_skills[:3])}",
                'suggested_action': 'Look for better matched candidates'
            }

    def generate_learning_suggestions(self, skill_analysis):
        """Generate learning suggestions for skill gaps"""
        suggestions = []

        for skill in skill_analysis:
            if skill['status'] in ['Missing', 'Partial']:
                gap = skill['required_years'] - skill['employee_years']

                suggestion = {
                    'skill_name': skill['skill_name'],
                    'current_level': skill['employee_years'],
                    'required_level': skill['required_years'],
                    'gap': gap,
                    'priority': 'High' if skill['is_mandatory'] else 'Medium',
                    'estimated_training_hours': int(gap * 40)  # Rough estimate
                }
                suggestions.append(suggestion)

        # Sort by priority and gap
        suggestions.sort(key=lambda x: (0 if x['priority'] == 'High' else 1, -x['gap']))

        return suggestions

    def validate_application(self, employee_skills, requirement_skills):
        """Main validation method"""
        match_percentage, skill_analysis = self.calculate_skill_match(
            employee_skills, requirement_skills
        )

        recommendation = self.get_recommendation(match_percentage, skill_analysis)
        learning_suggestions = self.generate_learning_suggestions(skill_analysis)

        return {
            'match_percentage': match_percentage,
            'ai_score': match_percentage,
            'ai_recommendation': recommendation['recommendation'],
            'recommendation_details': recommendation,
            'skill_analysis': skill_analysis,
            'learning_suggestions': learning_suggestions
        }
