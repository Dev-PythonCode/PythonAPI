# Python API Response Documentation

## Overview
The Python API parses natural language queries about job requirements and extracts structured entities for database queries.

## API Endpoint
**POST** `/parse`

### Request
```json
{
  "query": "Find Python developers with 5 years experience and sql knowledge, cloud technology is added advantage and located in Bangalore"
}
```

### Response Structure

```json
{
  "original_query": "string - The original user query",
  "parsed": {
    "skills": ["string - Required technologies"],
    "optional_skills": ["string - Nice-to-have technologies"],
    "categories": ["string - Technology categories detected"],
    "category_skills": ["string - Technologies expanded from categories"],
    "min_years_experience": "number - Minimum years required or null",
    "max_years_experience": "number - Maximum years required or null",
    "experience_operator": "string - 'gte' (>=), 'lte' (<=), 'eq' (==), 'between'",
    "experience_context": {
      "type": "string - 'skill_specific' or 'total'",
      "skill": "string - Skill this experience applies to, or null for total",
      "reason": "string - Why this was classified as such"
    },
    "skill_requirements": [
      {
        "skill": "string - Technology name",
        "min_years": "number",
        "max_years": "number or null",
        "operator": "string",
        "experience_type": "string"
      }
    ],
    "location": "string - Primary location (backward compatible)",
    "locations": ["string - All locations extracted"],
    "availability_status": {
      "status": "Available | Limited | Not Available | null",
      "keywords": ["string - Matched keywords"],
      "details": "string - Human-readable details or null"
    },
    "skill_levels": ["string - Expertise levels like 'Senior', 'Junior'"],
    "roles": ["string - Job titles like 'developer', 'engineer'"],
    "certifications": ["string - Required certifications"],
    "companies": ["string - Specific companies mentioned"],
    "dates": ["string - Time-related entities"]
  },
  "applied_filters": [
    "string - Human-readable filters for database query"
  ],
  "skills_found": "number - Total skills (required + category)",
  "entities_detected": {
    "skills": ["string - Required technologies"],
    "optional_skills": ["string - Nice-to-have technologies"],
    "categories": ["string - Tech categories"],
    "category_skills": ["string - Expanded skills"],
    "tech_experiences": ["string - Tech-specific experience mentions"],
    "overall_experiences": ["string - Overall experience mentions"],
    "locations": ["string - All locations"],
    "primary_location": "string - First location",
    "availability": {
      "status": "Available | Limited | Not Available | null",
      "keywords": ["string"],
      "details": "string or null"
    },
    "skill_levels": ["string"],
    "roles": ["string"],
    "certifications": ["string"],
    "companies": ["string"],
    "dates": ["string"]
  }
}
```

## Example Response

### Query
```
"Find Python developers with 5 years experience and sql knowledge, cloud technology is added advantage and located in Bangalore"
```

### Full Response
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

## Key Features

### 1. **Multi-Skill Extraction**
- Detects multiple technologies: Python, SQL
- Expands categories: Cloud Platform → AWS, Azure, GCP
- Optional skills marked separately

### 2. **Experience Extraction**
- Parses years of experience (5.0)
- Supports operators: >= (gte), <= (lte), == (eq)
- Per-skill requirements tracked

### 3. **Location Extraction**
- Supports multiple locations with "and", "or", ","
- Examples: "Chennai and Bangalore", "Manila or Colombo"

### 4. **Availability Status**
- **Available**: "immediate", "asap", "urgently"
- **Limited**: "part-time", "contract", "support"
- **Not Available**: "not available", "unavailable"

### 5. **Category Expansion**
- Cloud Platform → AWS, Azure, GCP
- Frontend Framework → React, Angular, Vue
- Backend Framework → Django, Flask, Spring
- Database → MySQL, PostgreSQL, MongoDB

### 6. **Applied Filters**
- Human-readable filter list for UI display
- Easy to show users what was understood

## Data Types & Ranges

| Field | Type | Range/Values |
|-------|------|--------------|
| min_years_experience | number \| null | 0-100 |
| max_years_experience | number \| null | 0-100 |
| experience_operator | string | 'gte', 'lte', 'eq', 'between' |
| availability.status | string \| null | 'Available', 'Limited', 'Not Available' |
| skills | array | Any of 87+ technologies |
| categories | array | 23 category names |
| roles | array | developer, engineer, architect, etc. |
| locations | array | 50+ city/region names |

## Supported Technologies (88 Total)

**Programming Languages**: Python, JavaScript, TypeScript, Java, C++, C#, Ruby, Go, Rust, PHP, Swift, Kotlin, Scala, R, MATLAB

**Cloud Platforms**: AWS, Azure, GCP

**Databases**: SQL, MySQL, PostgreSQL, MongoDB, Redis, SQLite, Oracle, Cassandra, Elasticsearch

**Frontend**: React, Angular, Vue, Svelte, Tailwind CSS, Bootstrap, Material UI

**Backend**: Django, Flask, Spring, Express, FastAPI, Laravel, ASP.NET

**DevOps**: Docker, Kubernetes, Jenkins, Terraform, Ansible

**More**: Git, GitHub, GitLab, Node.js, REST, GraphQL, JIRA, Figma, and 40+ more

## Supported Locations (50+)

**India**: Bangalore, Chennai, Delhi, Mumbai, Pune, Hyderabad, Trivandrum, Kolkata, and 20+ more

**SE Asia**: Manila, Colombo, Singapore, Bangkok

**Global**: New York, London, San Francisco, Toronto, Dubai, Sydney, etc.

## Error Handling

### Missing Query
```json
{
  "error": "Missing query parameter"
}
```

### Parse Error
```json
{
  "error": "Error description",
  "original_query": "user query",
  "parsed": {...default empty structure...},
  "applied_filters": [],
  "skills_found": 0
}
```

## Usage Examples

### Example 1: Multi-Location with Experience
**Query**: "Senior Python developer in Chennai and Bangalore with 8 years experience"
- skills: ['Python']
- locations: ['Chennai', 'Bangalore']
- min_years_experience: 8
- skill_levels: ['Senior']

### Example 2: Optional Skills with Availability
**Query**: "Java engineer part-time available in Manila, Colombo or Singapore"
- skills: ['Java']
- locations: ['Manila', 'Colombo', 'Singapore']
- availability_status: {status: 'Limited', details: 'Part-Time basis'}

### Example 3: Category with Multiple Skills
**Query**: "Cloud engineer with AWS and Azure expertise in NYC"
- categories: ['Cloud Platform']
- category_skills: ['AWS', 'Azure', 'GCP']
- locations: ['NYC']

## Notes

- **Normalization**: Technologies are normalized to canonical names (sql → SQL, phyton → Python)
- **Optional Skills**: Phrases with "added advantage", "bonus", "preferred" are marked as optional
- **Category Expansion**: When a category is mentioned, all technologies in that category are expanded
- **Backward Compatibility**: 'location' field always contains the first location; 'locations' field contains all
- **No SQL Queries**: This endpoint only parses and returns structured data; database queries are done by the UI/frontend

