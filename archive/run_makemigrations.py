"""
Script to handle makemigrations with automatic responses
"""
import subprocess
import sys

# Prepare answers for the prompts
answers = [
    'y',  # Was packorder.order_date renamed to packorder.ordered_at?
    'y',  # Was prescriptionitem.dispensed_date renamed to prescriptionitem.dispensed_at?
    '1',  # Provide a one-off default for batch_number
    "'LEGACY-BATCH'",  # Default value for batch_number (with quotes)
]

# Run makemigrations
process = subprocess.Popen(
    [sys.executable, 'manage.py', 'makemigrations'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Feed answers
for answer in answers:
    process.stdin.write(answer + '\n')
    process.stdin.flush()

# Close stdin and wait for completion
process.stdin.close()
output, _ = process.communicate()

# Print output
print(output)

# Return exit code
sys.exit(process.returncode)
