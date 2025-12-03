from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
from pathlib import Path
from config import Config
from services.resume_parser import ResumeParser
from services.query_parser import QueryParser
from services.vector_service import VectorService
from services.validator import ApplicationValidator

app = Flask(__name__)
CORS(app)
app.config.from_object(Config)

# Initialize services
resume_parser = None
query_parser = None
vector_service = None
validator = None


def init_services():
    global resume_parser, query_parser, vector_service, validator

    print("Initializing services...")
    resume_parser = ResumeParser()
    query_parser = QueryParser()
    vector_service = VectorService()
    validator = ApplicationValidator()
    print("Services initialized successfully!")


# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'services': {
            'resume_parser': resume_parser is not None,
            'query_parser': query_parser is not None,
            'vector_service': vector_service is not None,
            'validator': validator is not None
        },
        'vector_db_count': vector_service.get_stats()['count'] if vector_service else 0
    })


# Parse resume
@app.route('/parse', methods=['POST'])
def parse_resume():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            result = resume_parser.parse_resume(tmp_path)
            return jsonify(result)
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Parse natural language query and search with match calculation
@app.route('/chat', methods=['POST'])
def parse_and_search():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400

        query = data['query']

        # Step 1: Parse query using SpaCy NER
        parsed = query_parser.parse_query(query)

        # Step 2: Build search text for vector search
        search_parts = []
        if parsed['parsed']['skills']:
            search_parts.append(' '.join(parsed['parsed']['skills']))
        if parsed['parsed']['location']:
            search_parts.append(parsed['parsed']['location'])
        if parsed['parsed']['availability_status']:
            search_parts.append(parsed['parsed']['availability_status'])

        search_text = query if not search_parts else ' '.join(search_parts)

        # Step 3: Vector search with filters
        filters = {}
        if parsed['parsed']['location']:
            filters['location'] = parsed['parsed']['location']
        if parsed['parsed']['availability_status']:
            filters['availability'] = parsed['parsed']['availability_status']

        vector_results = vector_service.search(
            search_text,
            n_results=20,
            filters=filters if filters else None
        )

        # Step 4: Calculate match percentages for each result
        # This is NEW - adds match calculation based on parsed requirements
        enriched_results = []
        for result in vector_results:
            # Calculate match based on query requirements
            match_info = validator.calculate_query_match(
                employee_data=result,
                query_requirements=parsed['parsed']
            )

            # Merge vector similarity with detailed match analysis
            enriched_result = {
                **result,
                'detailed_match': match_info
            }
            enriched_results.append(enriched_result)

        # Sort by overall match percentage (not just vector similarity)
        enriched_results.sort(
            key=lambda x: x['detailed_match']['overall_match_percentage'],
            reverse=True
        )

        # Step 5: Return combined results
        return jsonify({
            **parsed,
            'vector_results': enriched_results,
            'search_text_used': search_text,
            'total_results': len(enriched_results)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Index single employee
@app.route('/vector/index', methods=['POST'])
def index_employee():
    try:
        data = request.get_json()
        if not data or 'employee_id' not in data:
            return jsonify({'error': 'No employee data provided'}), 400

        employee_id = data['employee_id']
        employee_data = data.get('employee_data', {})

        result = vector_service.index_employee(employee_id, employee_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Index multiple employees
@app.route('/vector/index-batch', methods=['POST'])
def index_batch():
    try:
        data = request.get_json()
        employees = data.get('employees', [])

        results = []
        for emp in employees:
            result = vector_service.index_employee(
                emp['employee_id'],
                emp
            )
            results.append(result)

        return jsonify({
            'indexed': len(results),
            'results': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Search employees with detailed matching
@app.route('/vector/search', methods=['POST'])
def search_employees():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400

        query = data['query']
        n_results = data.get('n_results', 20)
        filters = data.get('filters', None)

        results = vector_service.search(query, n_results, filters)

        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Delete employee from index
@app.route('/vector/delete/<int:employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    try:
        result = vector_service.delete_employee(employee_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Get vector DB stats
@app.route('/vector/stats', methods=['GET'])
def vector_stats():
    try:
        stats = vector_service.get_stats()
        return jsonify(stats)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Clear vector DB
@app.route('/vector/clear', methods=['POST'])
def clear_vector_db():
    try:
        result = vector_service.clear_all()
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Validate application
@app.route('/application/validate', methods=['POST'])
def validate_application():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        employee_skills = data.get('employee_skills', [])
        requirement_skills = data.get('requirement_skills', [])

        result = validator.validate_application(employee_skills, requirement_skills)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# View all indexed employees
@app.route('/vector/view-all', methods=['GET'])
def view_all_vectors():
    try:
        # Get all documents from collection
        results = vector_service.collection.get(
            include=["metadatas", "documents", "embeddings"]
        )

        employees = []
        if results['ids']:
            for i, emp_id in enumerate(results['ids']):
                employees.append({
                    'employee_id': emp_id,
                    'metadata': results['metadatas'][i] if results['metadatas'] else {},
                    'document': results['documents'][i] if results['documents'] else '',
                    'has_embedding': results['embeddings'] is not None
                })

        return jsonify({
            'total_count': len(employees),
            'employees': employees
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# View single employee
@app.route('/vector/view/<int:employee_id>', methods=['GET'])
def view_employee_vector(employee_id):
    try:
        results = vector_service.collection.get(
            ids=[str(employee_id)],
            include=["metadatas", "documents"]
        )

        if results['ids']:
            return jsonify({
                'employee_id': employee_id,
                'metadata': results['metadatas'][0] if results['metadatas'] else {},
                'document': results['documents'][0] if results['documents'] else ''
            })
        else:
            return jsonify({'error': 'Employee not found in vector DB'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Test query parsing
@app.route('/vector/test-parse', methods=['POST'])
def test_parse():
    try:
        data = request.get_json()
        query = data.get('query', '')

        # Parse query
        parsed = query_parser.parse_query(query)

        return jsonify({
            'query': query,
            'parsed': parsed,
            'entities': parsed.get('entities_detected', {})
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_services()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )