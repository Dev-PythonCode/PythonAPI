#!/usr/bin/env python3
"""
Test the improved /parse-requirement endpoint with skill-specific experience
"""

import requests
import json


def test_requirement_with_specific_skills():
    """Test parsing requirements with skill-specific experience"""
    
    url = "http://localhost:5000/parse-requirement"
    
    # Test case from user
    test_description = "Need a python developer with Python with 2 years and SQL Server with 2 years and 5 years of experience in Java Script"
    
    print("=" * 80)
    print("Testing Requirement Parsing with Skill-Specific Experience")
    print("=" * 80)
    print(f"\nDescription: {test_description}")
    print(f"\nSending request to {url}...")
    
    try:
        response = requests.post(
            url,
            json={"description": test_description},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ SUCCESS\n")
            print("=" * 80)
            print("EXTRACTED DATA:")
            print("=" * 80)
            
            extracted = result['extracted']
            
            print(f"\n📍 Location: {extracted.get('location', 'Not specified')}")
            print(f"👤 Roles: {', '.join(extracted.get('roles', [])) or 'Not specified'}")
            print(f"⭐ Seniority: {extracted.get('seniority', 'Not specified')}")
            print(f"📅 Overall Experience: {extracted.get('min_years_experience', 'Not specified')} years")
            
            print(f"\n🛠️  SKILLS ({extracted.get('skill_count', 0)} total):")
            print("-" * 80)
            
            if extracted.get('skills'):
                for i, skill in enumerate(extracted['skills'], 1):
                    name = skill.get('name')
                    years = skill.get('years', 0)
                    is_mandatory = skill.get('is_mandatory', False)
                    
                    # Format output
                    years_text = f"{years} years" if years > 0 else "No specific experience"
                    priority_icon = "⭐ MANDATORY" if is_mandatory else "💡 Nice-to-have"
                    
                    print(f"  {i}. {name}")
                    print(f"     Experience: {years_text}")
                    print(f"     Priority: {priority_icon}")
                    print()
            else:
                print("  No skills extracted")
            
            # Show what the C# form should display
            print("=" * 80)
            print("EXPECTED C# FORM BEHAVIOR:")
            print("=" * 80)
            if extracted.get('skills'):
                for skill in extracted['skills']:
                    print(f"  ✅ Skill: {skill['name']}")
                    print(f"     Min Years dropdown: {skill['years']}")
                    print(f"     Priority radio: {'Mandatory' if skill['is_mandatory'] else 'Nice to Have'}")
                    print()
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ CONNECTION ERROR: Could not connect to {url}")
        print("Make sure the Python API is running on port 5000")
        print("Run: python app.py")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
    
    print("\n" + "=" * 80)


def test_optional_skills():
    """Test parsing requirements with optional/good-to-have skills"""
    
    print("\n" + "=" * 80)
    print("Testing Optional Skills Detection")
    print("=" * 80)
    
    test_cases = [
        {
            "description": "Python developer with Django mandatory and React nice to have",
            "expected": {
                "Django": "Mandatory",
                "React": "Nice-to-have"
            }
        },
        {
            "description": "Java developer with Spring Boot required, Angular optional",
            "expected": {
                "Spring Boot": "Mandatory",
                "Angular": "Nice-to-have"
            }
        },
        {
            "description": "Developer with Python, JavaScript, and TypeScript (TypeScript good to have)",
            "expected": {
                "Python": "Mandatory",
                "JavaScript": "Mandatory",
                "TypeScript": "Nice-to-have"
            }
        }
    ]
    
    url = "http://localhost:5000/parse-requirement"
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Description: {test['description']}")
        
        try:
            response = requests.post(
                url,
                json={"description": test['description']},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                skills = result['extracted'].get('skills', [])
                
                print("Result:")
                for skill in skills:
                    priority = "Mandatory" if skill['is_mandatory'] else "Nice-to-have"
                    expected = test['expected'].get(skill['name'], 'N/A')
                    match = "✅" if priority.lower() == expected.lower() else "❌"
                    print(f"  {match} {skill['name']}: {priority} (expected: {expected})")
            else:
                print(f"  ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Test the specific user case
    test_requirement_with_specific_skills()
    
    # Test optional skills detection
    test_optional_skills()
    
    print("\n✅ Testing complete!\n")
