from matrix import *
import json
import random
from pathlib import Path

compress = random.randint(0, 100)
test = generate_matrix(difficulty=0, compressibility=compress)
print(f"low amount: {find_gods_number(test)}")
print(f"compress: {compress}%")
print("Original matrix:")
test.show_matrix()

while True:
    transformation = input("Enter a row transformation (or 'exit' to quit): ")
    if transformation.lower() == 'exit':
        break
    test.update(transformation)
    print("Updated matrix:")
    test.show_matrix()
    
    # Check if matrix is in RREF
    if test.is_rref():
        print(f"\n✓ Matrix is in RREF! Completed in {test.moves_count} moves!")
        
        # Save the number of moves to records.json
        records_file = Path("records.json")
        try:
            if records_file.exists():
                with open(records_file, "r") as f:
                    content = f.read().strip()
                    records = json.loads(content) if content else []
            else:
                records = []
        except (json.JSONDecodeError, IOError):
            records = []
        
        records.append(test.moves_count)
        
        with open(records_file, "w") as f:
            json.dump(records, f, indent=2)
        
        print(f"Saved to records.json")
        break