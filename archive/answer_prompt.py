import subprocess
import sys

# Run the makemigrations command and automatically answer the prompts
process = subprocess.Popen(
    [sys.executable, 'manage.py', 'makemigrations'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Send answers to all prompts:
# 1. 'N' for the first rename question (packorder.order_date -> ordered_at)
# 2. 'N' for the second rename question (prescriptionitem.dispensed_date -> dispensed_at)
# 3. '1' for the auto_now_add field addition (to provide a default)
# 4. '\n' for the default value (empty string which will use timezone.now)
# 5. '1' for the nullable field change (provide a one-off default)
# 6. '1' for the default value for the nullable field (use 1 as a placeholder)
answers = 'N\nN\n1\n\n1\n1\n'

try:
    stdout, stderr = process.communicate(input=answers, timeout=30)
    print("Output:")
    print(stdout)
    if stderr:
        print("Errors:")
        print(stderr)
    print(f"Return code: {process.returncode}")
except subprocess.TimeoutExpired:
    process.kill()
    stdout, stderr = process.communicate()
    print("Process timed out")
    print("Output:")
    print(stdout)
    if stderr:
        print("Errors:")
        print(stderr)