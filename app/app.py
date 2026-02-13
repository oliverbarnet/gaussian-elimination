from flask import Flask, render_template, request, session
import sys
import os

# Add parent directory to path to import matrix module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix import generate_matrix, find_gods_number

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

@app.route('/')
def index():
    # Generate a random matrix with random difficulty and compressibility
    import random
    difficulty = random.randint(0, 100)
    compressibility = random.randint(0, 100)
    
    matrix = generate_matrix(difficulty=difficulty, compressibility=compressibility)
    
    # Store matrix data in session
    session['matrix'] = {
        'size': matrix.size,
        'values': matrix.values,
        'outputs': matrix.outputs,
        'moves_count': 0,
        'start_time': None
    }
    session['difficulty'] = difficulty
    session['compressibility'] = compressibility
    session['mode'] = 'fmc'
    
    # Prepare data for template
    matrix_data = {
        'size': matrix.size,
        'coefficients': matrix.values,
        'augmented': matrix.outputs,
        'difficulty': difficulty,
        'compressibility': compressibility,
        'god_number': None,
        'moves': 0
    }
    
    # Get the estimated minimum moves
    god_num, _ = find_gods_number(matrix)
    matrix_data['god_number'] = god_num
    
    return render_template('index.html', matrix=matrix_data)

@app.route('/transform', methods=['POST'])
def transform():
    data = request.get_json()
    transformation = data.get('transformation', '').strip()
    mode = data.get('mode', 'fmc')
    time_elapsed = data.get('time_elapsed')
    
    if not transformation:
        return {'error': 'No transformation provided'}, 400
    
    # Recreate matrix from session
    from matrix import Matrix
    matrix_data = session.get('matrix')
    if not matrix_data:
        return {'error': 'No matrix in session'}, 400
    
    matrix = Matrix(matrix_data['size'], matrix_data['values'], matrix_data['outputs'])
    matrix.moves_count = matrix_data['moves_count']
    
    # Apply transformation
    matrix.update(transformation)
    
    # Update session
    session['matrix']['values'] = matrix.values
    session['matrix']['outputs'] = matrix.outputs
    session['matrix']['moves_count'] = matrix.moves_count
    session['mode'] = mode
    session.modified = True
    
    # Check if in RREF
    is_solved = matrix.is_rref()
    
    result = {
        'success': True,
        'coefficients': matrix.values,
        'augmented': matrix.outputs,
        'moves': matrix.moves_count,
        'is_solved': is_solved
    }
    
    # If solved, save to records and prepare new matrix
    if is_solved:
        from pathlib import Path
        import json
        from datetime import datetime
        
        # Save to records.json
        records_file = Path('/workspaces/gaussian-elimination/records.json')
        try:
            if records_file.exists():
                with open(records_file, "r") as f:
                    content = f.read().strip()
                    records = json.loads(content) if content else []
            else:
                records = []
        except (json.JSONDecodeError, IOError):
            records = []
        
        # Create record entry based on mode
        record_entry = {
            'mode': mode,
            'timestamp': datetime.now().isoformat()
        }
        
        if mode == 'fmc':
            record_entry['moves'] = matrix.moves_count
        else:  # timed mode
            record_entry['time'] = time_elapsed if time_elapsed else 0
        
        records.append(record_entry)
        
        with open(records_file, "w") as f:
            json.dump(records, f, indent=2)
        
        result['saved'] = True
    
    return result

@app.route('/new')
def new_matrix():
    return index()

if __name__ == '__main__':
    app.run(debug=True)
