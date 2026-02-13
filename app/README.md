# Flask Web App - Gaussian Elimination Matrix Generator

A simple Flask web application that displays randomly generated matrices for Gaussian elimination practice.

## Features

- **Random Matrix Generation** - Each page load generates a new matrix
- **Configurable Difficulty** - Coefficient range controlled by difficulty level (0-100)
- **Compressibility Control** - Determines how many moves are needed to solve (0-100)
- **Automatic Analysis** - Shows estimated minimum moves using the greedy algorithm
- **Responsive Design** - Works on desktop and mobile devices

## Installation

1. Install Flask:
```bash
pip install flask
```

2. Navigate to the app directory:
```bash
cd app
```

## Running the App

Start the Flask development server:
```bash
python app.py
```

The app will be available at `http://localhost:5000`

## How to Use

- Visit the homepage to see a randomly generated matrix
- Click "Generate New Matrix" to create a new matrix
- The info panel shows:
  - **Size**: Matrix dimensions (fixed at 3×3)
  - **Difficulty**: Coefficient range (0-100%)
  - **Compressibility**: How structured/solvable the matrix is (0-100%)
  - **Estimated Min Moves**: Minimum moves needed to solve (calculated by greedy algorithm)

## Parameters Explained

- **Difficulty (0-100)**:
  - 0 = small coefficients (1-10)
  - 100 = large coefficients (1-110)

- **Compressibility (0-100)**:
  - < 10 = highly structured, guaranteed < 9 moves needed
  - 50 = balanced
  - 100 = random coefficients, approaches 9 moves needed
