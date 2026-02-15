# Gaussian-Elimination

## How to Solve a 3x3 Matrix using Gaussian Elimination

Gaussian elimination is a step-by-step method to solve a system of linear equations. Here’s how you can solve a 3x3 matrix:

### Steps:

1. **Write the System of Equations in Matrix Form:**
   - Represent the system as an augmented matrix \[A|b\] where \[A\] is the 3x3 coefficient matrix, and \[b\] is the column vector of constants.

2. **Perform Row Operations:**
   - Use the following operations to transform the matrix into row-echelon form (triangular form):
      - Swap two rows.
      - Multiply a row by a nonzero constant.
      - Add or subtract a multiple of one row to another row.

3. **Eliminate Below the Pivot:**
   - Start with the top-left element (pivot) and make all elements below it zero by applying row operations.
   - Move to the next pivot on the diagonal, and repeat until the matrix is upper triangular.

4. **Solve using Back Substitution:**
   - Once the matrix is in row-echelon form, solve for the variables starting from the last row and working upwards.

### Example:

Solve the following system of equations:

\[
\begin{aligned}
2x +  y +  z &= 5 \\
4x + 3y +  z &= 6 \\
6x + 5y + 4z &= 9
\end{aligned}
\]

1. **Write in augmented matrix form:**

\[
\begin{bmatrix}
2 & 1 & 1 & | & 5 \\
4 & 3 & 1 & | & 6 \\
6 & 5 & 4 & | & 9
\end{bmatrix}
\]

2. **Row reduce to upper triangular form:**
   After performing row operations:

\[
\begin{bmatrix}
2 & 1 & 1 & | & 5 \\
0 & 1 & 1 & | & 1 \\
0 & 0 & 1 & | & 2
\end{bmatrix}
\]

3. **Solve using back substitution:**
   - From row 3: \( z = 2 \)
   - From row 2: \( y + z = 1 \to y = -1 \)
   - From row 1: \( 2x + y + z = 5 \to 2x - 1 + 2 = 5 \to x = 2 \)

### Final Solution:
\[
x = 2, \; y = -1, \; z = 2
\]