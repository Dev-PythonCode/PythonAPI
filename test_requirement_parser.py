#!/usr/bin/env python3
"""
Test script for the new /parse-requirement endpoint
"""

import requests
import json


def test_parse_requirement():
    """Test the requirement parsing endpoint"""
    
    url = "http://localhost:5000/parse-requirement"
    
    # Test cases
    test_cases = [
        {
            "description": "Need a senior Python developer with 5 years Django experience in Bangalore",
            "expected": {
                "skills": ["Python", "Django"],
                "location": "Bangalore"
            }
        },
        {
            "description": "Looking for Java and Spring Boot developer with 3+ years experience in Mumbai",
            "expected": {
                "skills": ["Java", "Spring Boot"],
                "location": "Mumbai"
            }
        },
        {
            "description": "Frontend developer needed with React, TypeScript and 4 years experience",
            "expected": {
                "skills": ["React", "TypeScript"]
            }
        },
        {
            "description": "Cloud architect with AWS, Docker, Kubernetes mandatory skills in Hyderabad",
            "expected": {
                "skills": ["AWS", "Docker", "Kubernetes"],
                "location": "Hyderabad"
            }
        }
    ]
    
    print("=" * 80)
    print("Testing /parse-requirement endpoint")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case {i}")
        print(f"{'='*80}")
        print(f"Description: {test_case['description']}")
        print(f"\nSending request to {url}...")
        
        try:
            response = requests.post(
                url,
                json={"description": test_case['description']},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"\n✅ SUCCESS")
                print(f"\nExtracted Data:")
                print(f"  Skills: {result['extracted'].get('skills', [])}")
                print(f"  Location: {result['extracted'].get('location')}")
                print(f"  Min Years Experience: {result['extracted'].get('min_years_experience')}")
                print(f"  Roles: {result['extracted'].get('roles')}")
                print(f"  Seniority: {result['extracted'].get('seniority')}")
                print(f"  Skill Count: {result['extracted'].get('skill_count')}")
                print(f"  Mandatory Count: {result['extracted'].get('mandatory_count')}")
                
                # Show detailed skill information
                if result['extracted'].get('skills'):
                    print(f"\n  Detailed Skills:")
                    for skill in result['extracted']['skills']:
                        mandatory_flag = "⭐ MANDATORY" if skill.get('is_mandatory') else "Nice-to-have"
                        years_text = f"{skill.get('years')} years" if skill.get('years') > 0 else "No specific experience"
                        print(f"    - {skill.get('name')}: {years_text} [{mandatory_flag}]")
            else:
                print(f"\n❌ ERROR: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"\n❌ CONNECTION ERROR: Could not connect to {url}")
            print("Make sure the Python API is running on port 5000")
            print("Run: python app.py")
            break
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
    
    print(f"\n{'='*80}")
    print("Testing Complete")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    test_parse_requirement()
