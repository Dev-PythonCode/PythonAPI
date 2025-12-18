# Quick Reference: API Response for GitHub Copilot

## TL;DR - The Complete API Response

```json
{
  "original_query": "Find Python developers with 5 years experience and sql knowledge, cloud technology is added advantage and located in Bangalore",
  
  "parsed": {
    "skills": ["Python", "SQL"],
    "optional_skills": [],
    "categories": ["Cloud Platform"],
    "category_skills": ["AWS", "Azure", "GCP"],
    "min_years_experience": 5.0,
    "max_years_experience": null,
    "experience_operator": "gte",
    "experience_context": {
      "type": "total",
      "skill": null,
      "reason": "OVERALL_EXPERIENCE entity detected, no specific skill mentioned"
    },
    "skill_requirements": [
      {
        "skill": "Python",
        "min_years": 5.0,
        "max_years": null,
        "operator": "gte",
        "experience_type": "skill_specific"
      },
      {
        "skill": "SQL",
        "min_years": 5.0,
        "max_years": null,
        "operator": "gte",
        "experience_type": "skill_specific"
      }
    ],
    "location": "Bangalore",
    "locations": ["Bangalore"],
    "availability_status": {
      "status": null,
      "keywords": [],
      "details": null
    },
    "skill_levels": [],
    "roles": ["developers"],
    "certifications": [],
    "companies": [],
    "dates": []
  },
  
  "applied_filters": [
    "Skills: Python, SQL",
    "Categories: Cloud Platform",
    "Python: 5.0+ years",
    "SQL: 5.0+ years",
    "Location: Bangalore",
    "Availability: {'status': None, 'keywords': [], 'details': None}"
  ],
  
  "skills_found": 5,
  
  "entities_detected": {
    "skills": ["Python", "SQL"],
    "optional_skills": [],
    "categories": ["Cloud Platform"],
    "category_skills": ["AWS", "Azure", "GCP"],
    "tech_experiences": [],
    "overall_experiences": ["with 5 years experience"],
    "locations": ["Bangalore"],
    "primary_location": "Bangalore",
    "availability": {
      "status": null,
      "keywords": [],
      "details": null
    },
    "skill_levels": [],
    "roles": ["developers"],
    "certifications": [],
    "companies": [],
    "dates": []
  }
}
```

## Key Fields Explained

| Field | Purpose | Example |
|-------|---------|---------|
| `skills` | Required technologies to find | ["Python", "SQL"] |
| `optional_skills` | Nice-to-have technologies | ["Kubernetes"] |
| `categories` | Technology domains | ["Cloud Platform"] |
| `category_skills` | All techs in detected categories | ["AWS", "Azure", "GCP"] |
| `min_years_experience` | Minimum years required | 5.0 |
| `experience_operator` | How to compare: gte (≥), lte (≤), eq (=), between | "gte" |
| `skill_requirements` | Per-skill experience breakdown | [{skill: "Python", min_years: 5}] |
| `locations` | All locations mentioned | ["Bangalore", "Chennai"] |
| `availability_status` | Work availability | {status: "Available"} |
| `roles` | Job positions | ["developer", "engineer"] |
| `applied_filters` | Human-readable filters for UI | ["Skills: Python, SQL", ...] |
| `skills_found` | Total unique skills | 5 |

## What Was Fixed

**Before**: SQL was ignored (not in tech dictionary)
```json
{
  "skills": ["Python"],  // ❌ Missing SQL
  "applied_filters": ["Skills: Python", "Python: 5.0+ years"]
}
```

**After**: SQL is now recognized
```json
{
  "skills": ["Python", "SQL"],  // ✅ SQL included
  "applied_filters": ["Skills: Python, SQL", "Python: 5.0+ years", "SQL: 5.0+ years"]
}
```

## 88 Supported Technologies (Updated)

### Programming Languages (15)
Python, JavaScript, TypeScript, Java, C++, C#, Ruby, Go, Rust, PHP, Swift, Kotlin, Scala, R, MATLAB

### Databases (9)
**SQL, MySQL, PostgreSQL, MongoDB, Redis, SQLite, Oracle, Cassandra, Elasticsearch**

### Cloud Platforms (3)
AWS, Azure, GCP

### Frontend (5)
React, Angular, Vue, Svelte, Tailwind CSS

### Backend (7)
Django, Flask, Spring, Express, FastAPI, Laravel, ASP.NET

### DevOps (5)
Docker, Kubernetes, Jenkins, Terraform, Ansible

### + More frameworks, tools, libraries (40+)

## 50+ Supported Locations

### India
Bangalore, Chennai, Delhi, Mumbai, Pune, Hyderabad, Trivandrum, Kolkata, Jaipur, Ahmedabad, Surat, Lucknow, Chandigarh, Indore, Kochi, Coimbatore, Vadodara, Ludhiana, Agra, Visakhapatnam, Patna, Raipur

### SE Asia
Manila, Colombo, Singapore, Bangkok

### Global
New York, London, San Francisco, Toronto, Dubai, Sydney, Seattle, Austin, Bay Area, Vancouver, and more

## 417 Normalization Mappings

Examples:
- "python" → "Python"
- "phyton" → "Python" (typo)
- "sql" → "SQL"
- "tsql" → "SQL"
- "pl/sql" → "SQL"
- "sql server" → "SQL"
- ".net" → "C#"
- "react" → "React"
- "nodejs" → "Node.js"

## Availability Status Mapping

```json
{
  "immediate": "Available",
  "asap": "Available",
  "urgently": "Available",
  "part-time": "Limited",
  "contract": "Limited",
  "support": "Limited",
  "not available": "Not Available",
  "unavailable": "Not Available"
}
```

## Files Created for You

1. **API_RESPONSE_EXAMPLE.json** - This exact JSON response
2. **API_DOCUMENTATION.md** - Full API documentation with all details
3. **ISSUE_RESOLUTION.md** - Root cause analysis and fix explanation
4. **QUICK_REFERENCE.md** - This file

## How to Use in Another Project

### Step 1: Copy the Response Structure
```python
# Use API_RESPONSE_EXAMPLE.json as reference
expected_response = {
    "original_query": str,
    "parsed": {...},
    "applied_filters": [...],
    "skills_found": int,
    "entities_detected": {...}
}
```

### Step 2: Parse the Query
```bash
curl -X POST http://localhost:5000/parse \
  -H "Content-Type: application/json" \
  -d '{"query": "your query here"}'
```

### Step 3: Use the Response
```javascript
// In your UI/frontend
const response = await api.parse(userQuery);

if (response.skills.length > 0) {
  // Use API results
  queryDatabase(response.parsed);
} else {
  // Use fallback
  showGenericResults();
}
```

## Common Queries & Responses

### Query 1: Multi-Tech with Experience
**Input**: "Python and Java developer with 8 years experience"
```json
{
  "skills": ["Python", "Java"],
  "min_years_experience": 8.0,
  "roles": ["developer"]
}
```

### Query 2: Optional Skills
**Input**: "React developer, Vue is a bonus, based in NYC"
```json
{
  "skills": ["React"],
  "optional_skills": [],  // Vue in category if available
  "locations": ["NYC"]
}
```

### Query 3: Multi-Location
**Input**: "Senior engineer in Bangalore and Chennai or Hyderabad"
```json
{
  "locations": ["Bangalore", "Chennai", "Hyderabad"],
  "skill_levels": ["Senior"]
}
```

### Query 4: Availability
**Input**: "Part-time QA automation engineer with Selenium"
```json
{
  "skills": ["Selenium"],
  "roles": ["QA automation engineer"],
  "availability_status": {
    "status": "Limited",
    "keywords": ["part-time"],
    "details": "Part-Time basis"
  }
}
```

## Troubleshooting

### Issue: Skills are empty
- **Cause**: Technology not in dictionary (like SQL was before)
- **Fix**: Add to `/data/tech_dict_with_categories.json` and `/data/normalization_map.json`

### Issue: Location not detected
- **Cause**: City not in common_locations list
- **Fix**: Add to the location list in `_extract_locations()` method

### Issue: Experience not parsed
- **Cause**: Years mentioned but not in expected format
- **Fix**: Query should contain number + "year(s)" or "exp(erience)"

### Issue: Fallback search triggered
- **Cause**: API response invalid or missing required fields
- **Fix**: Check applied_filters are non-empty and skills are valid

