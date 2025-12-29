# app.py
# Flask API for Natural Language Query Processing
# FIXED VERSION - No double wrapping in /parse endpoint

from flask import Flask, request, jsonify
from flask_cors import CORS
from services.query_parser import get_parser
from services.database import DatabaseService
from services.career_roadmap import get_roadmap_service
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
parser = get_parser()
db_service = DatabaseService()
roadmap_service = get_roadmap_service()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Just check if parser is loaded (skip database check for now)
        parser_healthy = parser is not None and parser.nlp is not None
        
        return jsonify({
            'status': 'healthy' if parser_healthy else 'degraded',
            'model_loaded': parser_healthy,
            'service': 'AI Talent Search API',
            'entity_types': parser.get_entity_types() if parser_healthy else []
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/parse', methods=['POST'])
def parse_query_endpoint():
    """
    Parse natural language query and extract entities

    ✅ FIXED: Returns result directly without extra wrapping
    """
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'error': 'Missing query parameter'
            }), 400

        query = data['query']

        logger.info(f"Parsing query: {query}")

        # Parse the query
        result = parser.parse_query(query)

        # ✅ Return result DIRECTLY - no extra wrapping!
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error parsing query: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'original_query': data.get('query', ''),
            'parsed': {
                'skills': [],
                'categories': [],
                'category_skills': [],
                'min_years_experience': None,
                'experience_operator': 'gte',
                'experience_context': None,
                'location': None,
                'availability_status': None,
                'skill_levels': [],
                'roles': [],
                'certifications': [],
                'companies': [],
                'dates': []
            },
            'applied_filters': [],
            'skills_found': 0
        }), 500


@app.route('/chat', methods=['POST'])
def chat_search():
    """
    Full search endpoint - parse query and return matching employees
    """
    try:
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({
                'error': 'Missing query parameter'
            }), 400

        query = data['query']

        logger.info(f"Processing search query: {query}")

        # Step 1: Parse the query
        parse_result = parser.parse_query(query)

        if 'error' in parse_result:
            return jsonify({
                'error': parse_result['error'],
                'original_query': query
            }), 500

        # Step 2: Extract search criteria
        parsed_data = parse_result['parsed']
        skills = parsed_data.get('skills', [])
        category_skills = parsed_data.get('category_skills', [])
        all_skills = list(set(skills + category_skills))

        min_years = parsed_data.get('min_years_experience')
        exp_operator = parsed_data.get('experience_operator', 'gte')
        exp_context = parsed_data.get('experience_context')
        location = parsed_data.get('location')
        availability = parsed_data.get('availability_status')

        logger.info(f"Search criteria - Skills: {all_skills}, Years: {min_years}, Location: {location}")

        # Step 3: Search database
        if not all_skills:
            logger.warning("No skills found in query")
            return jsonify({
                'original_query': query,
                'parsed': parsed_data,
                'results': [],
                'total_results': 0,
                'search_method': 'sql',
                'message': 'No skills detected in query'
            }), 200

        # Get matching employees
        employees = db_service.search_employees(
            skills=all_skills,
            min_years=min_years,
            operator=exp_operator,
            experience_context=exp_context,
            location=location,
            availability=availability
        )

        logger.info(f"Found {len(employees)} matching employees")

        # Step 4: Return results
        return jsonify({
            'original_query': query,
            'parsed': parsed_data,
            'results': employees,
            'total_results': len(employees),
            'search_method': 'sql'
        }), 200

    except Exception as e:
        logger.error(f"Error in chat search: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'original_query': data.get('query', ''),
            'results': [],
            'total_results': 0
        }), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get API statistics"""
    try:
        parser_stats = parser.get_stats()
        db_stats = db_service.get_stats()
        # Roadmap stats (training size)
        roadmap_stats = {}
        try:
            rs = roadmap_service
            roadmap_stats = {'training_entries': len(rs.training) if hasattr(rs, 'training') else 0}
        except Exception:
            roadmap_stats = {'training_entries': 0}

        return jsonify({
            'parser': parser_stats,
            'database': db_stats
            , 'career_roadmap': roadmap_stats
        }), 200
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/career_roadmap', methods=['POST'])
def career_roadmap():
    """
    Generate a career roadmap/skills plan for a user prompt.
    Also returns a list of open requirements matching the core skills.
    """
    try:
        data = request.get_json()

        if not data or 'prompt' not in data:
            return jsonify({'error': 'Missing prompt parameter'}), 400

        prompt = data['prompt']
        include_requirements = data.get('include_requirements', True)

        logger.info(f"Generating roadmap for prompt: {prompt}")

        roadmap = roadmap_service.generate_roadmap(prompt)
        
        # Add matching requirements info to response
        if include_requirements and 'recommended_skills' in roadmap:
            core_skills = roadmap.get('recommended_skills', [])
            requirements_info = roadmap_service.get_matching_requirements_by_skills(core_skills)
            roadmap['matching_requirements'] = {
                'core_skills_count': len(core_skills),
                'core_skills': core_skills,
                'search_note': 'To fetch actual job requirements, call /requirements endpoint with these core skills',
                'integration_hint': 'C# backend /api/requirements endpoint should filter by these skills'
            }

        return jsonify(roadmap), 200

    except Exception as e:
        logger.error(f"Error generating roadmap: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/skills', methods=['GET'])
def get_skills():
    """Get all available skills/technologies from training data"""
    try:
        skills_data = roadmap_service.get_all_skills()
        
        return jsonify(skills_data), 200

    except Exception as e:
        logger.error(f"Error getting skills: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'total_skills': 0,
            'skills': [],
            'categories': []
        }), 500


@app.route('/learning-paths', methods=['POST'])
def get_learning_paths():
    """
    Get learning paths for specified technologies
    
    Request:
    {
        "technologies": ["Python", "Docker", "AWS"],
        "difficulty_level": "Beginner"  (optional: "Beginner", "Intermediate", "Advanced")
    }
    
    Response:
    {
        "matched_technologies": {...},
        "learning_resources": {...},
        "sources": {...}
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'technologies' not in data:
            return jsonify({
                'error': 'Missing technologies parameter',
                'example': {
                    'technologies': ['Python', 'Docker'],
                    'difficulty_level': 'Beginner'
                }
            }), 400
        
        technologies = data.get('technologies', [])
        difficulty_level = data.get('difficulty_level', 'Beginner')
        
        if not isinstance(technologies, list):
            return jsonify({
                'error': 'technologies must be an array'
            }), 400
        
        # Load learning paths data
        import json
        import os
        learning_paths_file = os.path.join(os.path.dirname(__file__), 'data', 'learning_paths.json')
        
        with open(learning_paths_file, 'r') as f:
            learning_paths_data = json.load(f)
        
        # Collect results for requested technologies
        results = {
            'requested_technologies': technologies,
            'difficulty_level': difficulty_level,
            'matched_technologies': {},
            'not_found': [],
            'learning_resources': [],
            'total_resources': 0,
            'sources': learning_paths_data.get('sources', {}),
            'metadata': {
                'version': learning_paths_data.get('version'),
                'description': learning_paths_data.get('description'),
                'note': 'Learning paths can be extended with external API integrations'
            }
        }
        
        technologies_data = learning_paths_data.get('technologies', {})
        
        for tech in technologies:
            # Case-insensitive search
            tech_lower = tech.lower()
            found = False
            
            for tech_key, tech_info in technologies_data.items():
                if tech_key.lower() == tech_lower or tech_info.get('display_name', '').lower() == tech_lower:
                    results['matched_technologies'][tech_info['display_name']] = {
                        'display_name': tech_info['display_name'],
                        'category': tech_info['category'],
                        'difficulty_levels': tech_info['difficulty_levels'],
                        'learning_resources': {}
                    }
                    
                    # Get resources for requested difficulty level
                    resources_by_level = tech_info.get('learning_resources', {})
                    
                    if difficulty_level in resources_by_level:
                        results['matched_technologies'][tech_info['display_name']]['learning_resources'] = {
                            difficulty_level: resources_by_level[difficulty_level]
                        }
                        results['learning_resources'].extend(resources_by_level[difficulty_level])
                        results['total_resources'] += len(resources_by_level[difficulty_level])
                    else:
                        # Return all available levels if specific level not found
                        results['matched_technologies'][tech_info['display_name']]['learning_resources'] = resources_by_level
                        for level_resources in resources_by_level.values():
                            results['learning_resources'].extend(level_resources)
                            results['total_resources'] += len(level_resources)
                    
                    found = True
                    break
            
            if not found:
                results['not_found'].append(tech)
        
        logger.info(f"Learning paths requested for: {technologies}")
        
        return jsonify(results), 200
    
    except FileNotFoundError:
        logger.error("Learning paths data file not found")
        return jsonify({
            'error': 'Learning paths data not found',
            'message': 'data/learning_paths.json is missing'
        }), 500
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON in learning paths file")
        return jsonify({
            'error': 'Invalid learning paths data format'
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting learning paths: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve learning paths'
        }), 500


@app.route('/learning-paths/all', methods=['GET'])
def get_all_learning_paths():
    """
    Get all available learning paths and technologies
    
    Query parameters (optional):
    - category: Filter by category (e.g., "Programming Language", "Frontend Framework")
    - limit: Limit number of technologies (default: no limit)
    """
    try:
        import json
        import os
        
        learning_paths_file = os.path.join(os.path.dirname(__file__), 'data', 'learning_paths.json')
        
        with open(learning_paths_file, 'r') as f:
            learning_paths_data = json.load(f)
        
        # Optional category filter
        category_filter = request.args.get('category')
        limit = request.args.get('limit', type=int)
        
        technologies_data = learning_paths_data.get('technologies', {})
        
        # Build response
        technologies_list = []
        for tech_key, tech_info in technologies_data.items():
            if category_filter and tech_info.get('category') != category_filter:
                continue
            
            technologies_list.append({
                'display_name': tech_info['display_name'],
                'category': tech_info['category'],
                'difficulty_levels': tech_info['difficulty_levels'],
                'resource_count': sum(len(resources) for resources in tech_info.get('learning_resources', {}).values())
            })
        
        if limit:
            technologies_list = technologies_list[:limit]
        
        return jsonify({
            'total_technologies': len(technologies_list),
            'technologies': technologies_list,
            'categories': list(set(t['category'] for t in technologies_list)),
            'sources': learning_paths_data.get('sources', {}),
            'metadata': learning_paths_data.get('metadata', {})
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting all learning paths: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'message': 'Failed to retrieve learning paths'
        }), 500


if __name__ == '__main__':
    logger.info("Starting Flask API...")
    logger.info(f"Parser loaded: {parser.nlp is not None}")
    logger.info(f"Entity types: {parser.get_entity_types()}")
    
    import os
    port = int(os.environ.get("FLASK_PORT", 5000))
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )

