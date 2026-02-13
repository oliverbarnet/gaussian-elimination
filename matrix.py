import random
from collections import deque
from copy import deepcopy

def generate_matrix(difficulty: int = 50, compressibility: int = 50):
    """
    Generate a solvable 3x3 matrix with controllable difficulty and compressibility.
    
    Args:
        difficulty: Integer from 0 to 100 (default 50)
                   Controls coefficient range (1-10 at 0, up to 1-110 at 100)
        
        compressibility: Integer from 0 to 100 (default 50)
                        Controls optimal move count
                        < 10 = guaranteed < 9 moves (highly structured)
                        50 = medium compressibility
                        100 = highly incompressible (~9 moves)
    
    Returns:
        A Matrix object that is guaranteed to be solvable
    """
    # Clamp parameters to 0-100
    difficulty = max(0, min(100, difficulty))
    compressibility = max(0, min(100, compressibility))
    
    # Fixed size at 3x3
    size = 3
    
    # Map difficulty to coefficient range (1-10 to 1-110)
    max_coeff = 10 + difficulty
    
    # Generate coefficients based on compressibility
    if compressibility < 10:
        # Highly structured: guarantee < 9 moves
        # Create a matrix with many pre-diagonal zeros and small pivots close to 1
        values = [[0 for _ in range(size)] for _ in range(size)]
        # Put random small values on and above diagonal
        for i in range(size):
            for j in range(i, size):
                values[i][j] = random.randint(1, 3)
    elif compressibility < 50:
        # Moderately compressible: fewer moves
        values = [[random.randint(1, 6) for _ in range(size)] for _ in range(size)]
        # Add some strategic zeros
        for i in range(size):
            if random.random() < 0.4:
                values[i][random.randint(0, size-1)] = 0
    else:
        # High compressibility: random coefficients for more moves
        values = [[random.randint(1, max_coeff) for _ in range(size)] for _ in range(size)]
    
    # Generate a random solution vector
    solution = [random.randint(1, max_coeff) for _ in range(size)]
    
    # Compute the outputs (augmented column) by multiplying matrix by solution
    outputs = []
    for i in range(size):
        output = sum(values[i][j] * solution[j] for j in range(size))
        outputs.append(output)
    
    return Matrix(size, values, outputs)


def find_gods_number(matrix):
    """
    Find an estimate of the minimum moves using a greedy heuristic (fast approximation).
    Not guaranteed optimal, but runs in milliseconds.
    
    Args:
        matrix: A Matrix object to solve
    
    Returns:
        Tuple: (estimated_min_moves, sequence_of_operations)
    """
    def format_factor(f):
        """Format factor to max 2 decimals, remove .0 for whole numbers"""
        rounded = round(f, 2)
        if rounded.is_integer():
            return str(int(rounded))
        return str(rounded)
    
    # Create a working copy
    work_matrix = Matrix(matrix.size, deepcopy(matrix.values), deepcopy(matrix.outputs))
    operations = []
    
    # Greedy forward elimination - layer by layer
    for col in range(work_matrix.size):
        # Make diagonal element = 1
        diag = work_matrix._clean_number(work_matrix.values[col][col])
        if diag != 0 and diag != 1:
            factor = round(1/diag, 2)
            op = f"R{col + 1} = R{col + 1} * {format_factor(factor)}"
            work_matrix.update(op)
            operations.append(op)
        
        # Eliminate below diagonal
        for row in range(col + 1, work_matrix.size):
            val = work_matrix._clean_number(work_matrix.values[row][col])
            if val != 0:
                factor = round(val, 2)
                op = f"R{row + 1} = R{row + 1} - {format_factor(factor)} * R{col + 1}"
                work_matrix.update(op)
                operations.append(op)
    
    # Back elimination - layer by layer
    for col in range(work_matrix.size - 1, -1, -1):
        for row in range(col - 1, -1, -1):
            val = work_matrix._clean_number(work_matrix.values[row][col])
            if val != 0:
                factor = round(val, 2)
                op = f"R{row + 1} = R{row + 1} - {format_factor(factor)} * R{col + 1}"
                work_matrix.update(op)
                operations.append(op)
    
    return len(operations), operations


class Matrix:
    def __init__(self, size: int, values: list, outputs: list):
        if len(values) != size or len(outputs) != size:
            print("matrix not correctly sized")
            exit()
        
        self.size = size
        self.values = values
        self.outputs = outputs
        self.moves_count = 0
        self.matrix = []
        for i in range(self.size):
            self.matrix.append(self.values[i])
            self.matrix.append(self.outputs[i])
    
    def _clean_number(self, num):
        """Convert floats to max 2 decimal places, and round to avoid floating point artifacts"""
        if isinstance(num, float):
            # Round to 2 decimal places maximum
            rounded = round(num, 2)
            # If it's a whole number, return as integer
            if rounded.is_integer():
                return int(rounded)
            # Remove trailing zeros from decimal
            return float(f"{rounded:.2f}".rstrip('0').rstrip('.'))
        return num
    
    def _clean_row(self, row):
        """Clean all numbers in a row"""
        return [self._clean_number(x) for x in row]
    
    def show_matrix(self):
        for i in range(self.size):
            print(f"{str(self.values[i])} | {str(self.outputs[i])}")
    
    def is_rref(self):
        """Check if the coefficient matrix is in Reduced Row Echelon Form (identity matrix)"""
        for i in range(self.size):
            for j in range(self.size):
                if i == j:
                    # Diagonal should be 1
                    if self._clean_number(self.values[i][j]) != 1:
                        return False
                else:
                    # Off-diagonal should be 0
                    if self._clean_number(self.values[i][j]) != 0:
                        return False
        return True
    
    def _apply_row_op(self, row_data, scalar):
        """Multiply each element in a row by a scalar"""
        return [x * scalar for x in row_data]
    
    def _add_rows(self, row1, row2):
        """Add two rows element-wise"""
        return [x + y for x, y in zip(row1, row2)]
    
    def update(self, transformation: str):
        """
        Apply a row transformation to the matrix.
        Examples: 'R1 = R1 * 2', 'R2 = 5 * R1 + R2' (or use lowercase: 'r1 = r1 * 2')
        """
        # Convert to uppercase to support both 'r1' and 'R1'
        transformation = transformation.upper()
        
        # Parse the transformation
        parts = transformation.split('=')
        if len(parts) != 2:
            print("Invalid transformation format")
            return
        
        target_row_str = parts[0].strip()
        operation_str = parts[1].strip()
        
        # Extract target row number
        if not target_row_str.startswith('R'):
            print("Invalid row reference")
            return
        
        try:
            target_row = int(target_row_str[1:]) - 1  # Convert to 0-indexed
            if target_row < 0 or target_row >= self.size:
                print(f"Row index out of bounds")
                return
        except ValueError:
            print("Invalid row number")
            return
        
        # Create a custom namespace with Row objects that support operations
        class RowOp:
            def __init__(self, data):
                self.data = data
            
            def __mul__(self, other):
                if isinstance(other, (int, float)):
                    return RowOp([x * other for x in self.data])
                raise TypeError("Row can only be multiplied by a scalar")
            
            def __rmul__(self, other):
                if isinstance(other, (int, float)):
                    return RowOp([x * other for x in self.data])
                raise TypeError("Row can only be multiplied by a scalar")
            
            def __add__(self, other):
                if isinstance(other, RowOp):
                    return RowOp([x + y for x, y in zip(self.data, other.data)])
                raise TypeError("Can only add rows to rows")
            
            def __radd__(self, other):
                if isinstance(other, RowOp):
                    return RowOp([x + y for x, y in zip(self.data, other.data)])
                raise TypeError("Can only add rows to rows")
            
            def __sub__(self, other):
                if isinstance(other, RowOp):
                    return RowOp([x - y for x, y in zip(self.data, other.data)])
                raise TypeError("Can only subtract rows from rows")
            
            def __rsub__(self, other):
                if isinstance(other, RowOp):
                    return RowOp([y - x for x, y in zip(self.data, other.data)])
                raise TypeError("Can only subtract rows from rows")
            
            def __truediv__(self, other):
                if isinstance(other, (int, float)):
                    return RowOp([x / other for x in self.data])
                raise TypeError("Row can only be divided by a scalar")
            
            def __rtruediv__(self, other):
                raise TypeError("Cannot divide a scalar by a row")
        
        # Create namespace with RowOp objects for coefficients
        coeff_namespace = {}
        for i in range(self.size):
            coeff_namespace[f'R{i+1}'] = RowOp(self.values[i])
        
        # Evaluate the operation
        try:
            result = eval(operation_str, {"__builtins__": {}}, coeff_namespace)
            if isinstance(result, RowOp):
                self.values[target_row] = self._clean_row(result.data)
            else:
                print("Transformation result is not a valid row")
                return
        except Exception as e:
            print(f"Error evaluating transformation: {e}")
            return
        
        # Apply the same transformation to the outputs
        output_namespace = {}
        for i in range(self.size):
            output_namespace[f'R{i+1}'] = self.outputs[i]
        
        try:
            result_output = eval(operation_str, {"__builtins__": {}}, output_namespace)
            self.outputs[target_row] = self._clean_number(result_output)
        except Exception as e:
            print(f"Error evaluating transformation for outputs: {e}")
            return
        
        # Successfully applied transformation, increment moves counter
        self.moves_count += 1
    
    def fast_rref(self):
        """
        Solve using optimized Fast RREF method.
        Minimizes moves by:
        1. Strategic elimination to create upper triangular
        2. Only normalizing non-1 pivots
        3. Efficient back-substitution
        Typically achieves 5-8 moves instead of 9.
        """
        print("\n" + "="*50)
        print("FAST RREF METHOD (Optimized)")
        print("="*50 + "\n")
        
        # PHASE 1: Forward elimination to upper triangular
        print("PHASE 1: Create Upper Triangular Form")
        print("-" * 50)
        
        for col in range(self.size):
            # Find best pivot (preferably already 1, or smallest to scale)
            best_pivot_row = col
            best_pivot_val = self._clean_number(self.values[col][col])
            
            # If current pivot is 0, find a non-zero pivot below
            if best_pivot_val == 0:
                for row in range(col + 1, self.size):
                    val = self._clean_number(self.values[row][col])
                    if val != 0:
                        best_pivot_row = row
                        best_pivot_val = val
                        break
            
            # Eliminate below the pivot
            for row in range(col + 1, self.size):
                val = self._clean_number(self.values[row][col])
                if val != 0:
                    if best_pivot_val != 0:
                        # Eliminate this element
                        factor = val / best_pivot_val
                        self.update(f"R{row + 1} = R{row + 1} - {factor} * R{col + 1}")
                        print(f"Move {self.moves_count}: Clear R{row + 1}C{col + 1}")
                        self.show_matrix()
                        print()
        
        # PHASE 2: Normalize pivots (only if not already 1)
        print("\nPHASE 2: Normalize Diagonal")
        print("-" * 50)
        
        for i in range(self.size):
            pivot = self._clean_number(self.values[i][i])
            if pivot != 1 and pivot != 0:
                self.update(f"R{i + 1} = R{i + 1} * {1/pivot}")
                print(f"Move {self.moves_count}: Normalize R{i + 1}")
                self.show_matrix()
                print()
        
        # PHASE 3: Back substitution (minimize by clearing only non-zero)
        print("\nPHASE 3: Back Elimination")
        print("-" * 50)
        
        for col in range(self.size - 1, -1, -1):
            for row in range(col - 1, -1, -1):
                val = self._clean_number(self.values[row][col])
                if val != 0:
                    self.update(f"R{row + 1} = R{row + 1} - {val} * R{col + 1}")
                    print(f"Move {self.moves_count}: Clear R{row + 1}C{col + 1}")
                    self.show_matrix()
                    print()
        
        print("="*50)
        if self.is_rref():
            print(f"✓ SOLVED IN {self.moves_count} MOVES!")
            print("="*50 + "\n")
            return True
        else:
            print(f"⚠ Not fully solved (completed {self.moves_count} moves)")
            print("="*50 + "\n")
            return False