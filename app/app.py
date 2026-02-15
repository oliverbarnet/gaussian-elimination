from flask import Flask, render_template, request, session, redirect, url_for
import sys
import os
import random
import json
from datetime import datetime
from functools import wraps
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash

# Add parent directory to path to import matrix module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix import generate_matrix, find_gods_number

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

APP_DIR = Path(__file__).resolve().parent
USERS_FILE = APP_DIR / 'users.json'


def load_users():
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            users = json.loads(content) if content else {}
            # Backfill schema for older accounts.
            for username, user in users.items():
                if not isinstance(user, dict):
                    users[username] = {'password_hash': '', 'timed_records': [], 'elo': 0}
                    continue
                user.setdefault('timed_records', [])
                user.setdefault('elo', 0)
                users[username] = user
            return users
    except (json.JSONDecodeError, OSError):
        return {}


def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2)


def compute_leaderboard(users):
    rows = []
    for username, user in users.items():
        records = user.get('timed_records', [])
        times = [
            r.get('time', 0)
            for r in records
            if r.get('mode') == 'leaderboard' and isinstance(r.get('time', 0), (int, float))
        ]
        if not times:
            continue
        avg_time = sum(times) / len(times)
        rows.append({
            'username': username,
            'average_time': avg_time,
            'solve_count': len(times)
        })
    rows.sort(key=lambda row: row['average_time'])
    return rows


def ranked_threshold_for_elo(elo):
    # Higher ELO means a stricter (lower) time threshold.
    # ELO 0 -> ~30.00s threshold, ELO 15000 -> ~6.00s threshold.
    clamped = max(0.0, min(15000.0, float(elo)))
    progress = (clamped / 15000.0) ** 0.9
    return 30.0 - (24.0 * progress)


def calculate_ranked_elo_delta(elo, solve_time):
    threshold = ranked_threshold_for_elo(elo)
    elo_factor = max(0.0, min(1.0, float(elo) / 15000.0))
    if solve_time <= threshold:
        # Good solve: reward scales up to +50 for strong overperformance.
        performance = min(1.0, (threshold - solve_time) / max(threshold, 1.0))
        delta = int(round(20 + (30 * (performance ** 0.65))))
    else:
        # Bad solve: softer penalties than rewards, with mild high-ELO scaling.
        performance = min(1.0, (solve_time - threshold) / max(threshold, 1.0))
        penalty = 1 + (20 * (performance ** 0.9)) + (8 * elo_factor * performance)
        delta = -int(round(penalty))

    # Clamp absolute ELO movement to 15..50.
    if delta > 0:
        delta = max(15, min(50, delta))
    else:
        delta = -max(15, min(50, abs(delta)))
    return delta, threshold


def compute_fastest_runs(users, limit=25):
    best_by_user = {}
    for username, user in users.items():
        records = user.get('timed_records', [])
        for record in records:
            if record.get('mode') != 'leaderboard':
                continue
            time_val = record.get('time')
            if not isinstance(time_val, (int, float)):
                continue
            candidate = {
                'username': username,
                'time': float(time_val),
                'seed': record.get('seed'),
                'timestamp': record.get('timestamp', '')
            }
            current_best = best_by_user.get(username)
            if current_best is None or candidate['time'] < current_best['time']:
                best_by_user[username] = candidate
    runs = list(best_by_user.values())
    runs.sort(key=lambda run: run['time'])
    return runs[:limit]


def compute_user_stats(user):
    records = user.get('timed_records', [])
    best = {
        'fmc': None,
        'timed': None,
        'seeded': None,
        'leaderboard': None,
        'ranked': None
    }
    counts = {
        'fmc': 0,
        'timed': 0,
        'seeded': 0,
        'leaderboard': 0,
        'ranked': 0
    }

    for record in records:
        mode = record.get('mode')
        if mode not in best:
            continue
        counts[mode] += 1
        if mode == 'fmc':
            moves = record.get('moves')
            if isinstance(moves, int):
                if best['fmc'] is None or moves < best['fmc']:
                    best['fmc'] = moves
        else:
            time_val = record.get('time')
            if isinstance(time_val, (int, float)):
                time_val = float(time_val)
                if best[mode] is None or time_val < best[mode]:
                    best[mode] = time_val

    return {
        'best': best,
        'counts': counts
    }


def compute_elo_leaderboard(users):
    rows = []
    for username, user in users.items():
        records = user.get('timed_records', [])
        ranked_count = sum(1 for r in records if r.get('mode') == 'ranked')
        rows.append({
            'username': username,
            'elo': int(user.get('elo', 0)),
            'ranked_count': ranked_count
        })
    rows.sort(key=lambda row: (-row['elo'], row['username'].lower()))
    return rows


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('index'))
        return fn(*args, **kwargs)
    return wrapper


def debug_user_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get('username') != 'aaa':
            return {'error': 'Forbidden'}, 403
        return fn(*args, **kwargs)
    return wrapper


def build_and_render_game():
    users = load_users()
    current_user = users.get(session.get('username', ''), {})
    current_elo = int(current_user.get('elo', 0))

    initial_mode = request.args.get('mode', 'fmc')
    if initial_mode not in ('fmc', 'timed', 'seeded', 'leaderboard', 'ranked'):
        initial_mode = 'fmc'
    auto_start_timed = request.args.get('autostart') == '1'
    requested_seed = request.args.get('seed')
    if initial_mode in ('leaderboard', 'ranked'):
        requested_seed = None

    seed_value = None
    if requested_seed not in (None, ''):
        try:
            seed_value = int(requested_seed)
        except ValueError:
            seed_value = None
    if seed_value is None:
        seed_value = random.randint(100000, 999999)

    # One seed always maps to one matrix in every mode.
    seed_rng = random.Random(seed_value)
    if initial_mode == 'ranked':
        # Keep ranked matrices in a tighter band to avoid extreme spikes.
        difficulty = seed_rng.randint(1, 20)
        compressibility = seed_rng.randint(1, 20)
    else:
        difficulty = seed_rng.randint(0, 100)
        compressibility = seed_rng.randint(0, 100)

    matrix = generate_matrix(
        difficulty=difficulty,
        compressibility=compressibility,
        seed=seed_value
    )

    session['matrix'] = {
        'size': matrix.size,
        'values': matrix.values,
        'outputs': matrix.outputs,
        'moves_count': 0,
        'start_time': None,
        'seed': seed_value
    }
    session['difficulty'] = difficulty
    session['compressibility'] = compressibility
    session['mode'] = initial_mode

    matrix_data = {
        'size': matrix.size,
        'coefficients': matrix.values,
        'augmented': matrix.outputs,
        'difficulty': difficulty,
        'compressibility': compressibility,
        'god_number': None,
        'moves': 0,
        'seed': seed_value
    }

    god_num, _ = find_gods_number(matrix)
    matrix_data['god_number'] = god_num

    return render_template(
        'index.html',
        matrix=matrix_data,
        initial_mode=initial_mode,
        auto_start_timed=auto_start_timed,
        selected_seed=seed_value,
        username=session.get('username', ''),
        is_debug_user=session.get('username') == 'aaa',
        current_elo=current_elo,
        ranked_threshold=ranked_threshold_for_elo(current_elo)
    )


@app.route('/')
def index():
    if 'username' not in session:
        auth_mode = request.args.get('auth', 'signin')
        if auth_mode not in ('signin', 'signup'):
            auth_mode = 'signin'
        return render_template('auth.html', auth_mode=auth_mode, error=None, success=None)
    return build_and_render_game()


@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if len(username) < 3:
        return render_template('auth.html', auth_mode='signup', error='Username must be at least 3 characters.', success=None)
    if len(password) < 6:
        return render_template('auth.html', auth_mode='signup', error='Password must be at least 6 characters.', success=None)

    users = load_users()
    if username in users:
        return render_template('auth.html', auth_mode='signup', error='Username already exists.', success=None)

    users[username] = {
        'password_hash': generate_password_hash(password),
        'timed_records': [],
        'elo': 0
    }
    save_users(users)
    session['username'] = username
    return redirect(url_for('index'))


@app.route('/signin', methods=['POST'])
def signin():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    users = load_users()
    user = users.get(username)
    if not user or not check_password_hash(user.get('password_hash', ''), password):
        return render_template('auth.html', auth_mode='signin', error='Invalid username or password.', success=None)

    session['username'] = username
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/transform', methods=['POST'])
@login_required
def transform():
    data = request.get_json()
    transformation = data.get('transformation', '').strip()
    mode = data.get('mode', 'fmc')
    time_elapsed = data.get('time_elapsed')

    if not transformation:
        return {'error': 'No transformation provided'}, 400

    from matrix import Matrix
    matrix_data = session.get('matrix')
    if not matrix_data:
        return {'error': 'No matrix in session'}, 400

    matrix = Matrix(matrix_data['size'], matrix_data['values'], matrix_data['outputs'])
    matrix.moves_count = matrix_data['moves_count']
    matrix.update(transformation)

    session['matrix']['values'] = matrix.values
    session['matrix']['outputs'] = matrix.outputs
    session['matrix']['moves_count'] = matrix.moves_count
    session['mode'] = mode
    session.modified = True

    is_solved = matrix.is_rref()
    result = {
        'success': True,
        'coefficients': matrix.values,
        'augmented': matrix.outputs,
        'moves': matrix.moves_count,
        'is_solved': is_solved,
        'seed': session.get('matrix', {}).get('seed')
    }

    # Save solved run to the signed-in account (leaderboard ranking only
    # uses records where mode == 'leaderboard').
    if is_solved:
        users = load_users()
        username = session.get('username')
        user = users.get(username)
        if user is not None:
            records = user.get('timed_records', [])
            record_entry = {
                'mode': mode,
                'timestamp': datetime.now().isoformat(),
                'seed': session.get('matrix', {}).get('seed')
            }
            if mode == 'fmc':
                record_entry['moves'] = matrix.moves_count
            else:
                try:
                    record_entry['time'] = round(float(time_elapsed), 2)
                except (TypeError, ValueError):
                    record_entry['time'] = 0.0
            if mode == 'ranked':
                current_elo = int(user.get('elo', 0))
                solve_time = float(record_entry.get('time', 0.0))
                elo_delta, threshold = calculate_ranked_elo_delta(current_elo, solve_time)
                new_elo = max(0, min(15000, current_elo + elo_delta))
                user['elo'] = new_elo
                record_entry['threshold'] = round(threshold, 2)
                record_entry['elo_before'] = current_elo
                record_entry['elo_after'] = new_elo
                record_entry['elo_delta'] = elo_delta
                result['elo_before'] = current_elo
                result['elo_after'] = new_elo
                result['elo_delta'] = elo_delta
                result['ranked_threshold'] = round(threshold, 2)
            records.append(record_entry)
            user['timed_records'] = records
            users[username] = user
            save_users(users)
            result['saved'] = True

    return result


@app.route('/new')
@login_required
def new_matrix():
    return build_and_render_game()


@app.route('/leaderboard')
@login_required
def leaderboard():
    users = load_users()
    leaderboard_rows = compute_leaderboard(users)
    fastest_runs = compute_fastest_runs(users)
    elo_rows = compute_elo_leaderboard(users)
    return render_template(
        'leaderboard.html',
        rows=leaderboard_rows,
        fastest_runs=fastest_runs,
        elo_rows=elo_rows,
        username=session.get('username', '')
    )


@app.route('/stats')
@login_required
def stats():
    users = load_users()
    username = session.get('username')
    user = users.get(username, {'timed_records': []})
    stats_data = compute_user_stats(user)
    return render_template(
        'stats.html',
        username=username,
        best=stats_data['best'],
        counts=stats_data['counts'],
        elo=int(user.get('elo', 0)),
        ranked_threshold=ranked_threshold_for_elo(int(user.get('elo', 0)))
    )


@app.route('/debug/clear_all_records', methods=['POST'])
@login_required
@debug_user_required
def debug_clear_all_records():
    users = load_users()
    for username, user in users.items():
        user['timed_records'] = []
        users[username] = user
    save_users(users)
    return {'success': True}


@app.route('/debug/clear_my_records', methods=['POST'])
@login_required
@debug_user_required
def debug_clear_my_records():
    users = load_users()
    username = session.get('username')
    user = users.get(username)
    if user is None:
        return {'error': 'User not found'}, 404
    user['timed_records'] = []
    users[username] = user
    save_users(users)
    return {'success': True}


if __name__ == '__main__':
    app.run(debug=True)
