#!/usr/bin/env python
"""
Test Runner for Playwright Pharmacy Tests
Run comprehensive Playwright tests for the HMS Pharmacy system

Usage:
    python run_playwright_tests.py --help
    python run_playwright_tests.py --all
    python run_playwright_tests.py --bulk-store
    python run_playwright_tests.py --transfers
    python run_playwright_tests.py --edge-cases
"""

import argparse
import os
import sys
import subprocess
import time
from datetime import datetime


class TestRunner:
    """Test runner for Playwright tests"""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_file = os.path.join(self.base_dir, 'tests_playwright_pharmacy.py')
        self.results_dir = os.path.join(self.base_dir, 'test_results')
        os.makedirs(self.results_dir, exist_ok=True)

    def install_playwright(self):
        """Install Playwright browsers"""
        print("="*80)
        print("Installing Playwright browsers...")
        print("="*80)
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'firefox'], check=True)
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'webkit'], check=True)
        print("✓ Playwright browsers installed successfully\n")

    def run_tests(self, test_group: str = None, verbose: bool = False, headless: bool = False):
        """Run test suite"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.results_dir, f'report_{timestamp}.html')

        cmd = [
            sys.executable, '-m', 'pytest',
            self.test_file,
            '--html', report_file,
            '--self-contained-html',
            '-v' if verbose else '-q',
        ]

        if test_group:
            cmd.extend(['-m', test_group])

        if headless:
            cmd.append('--headless')

        # Add screenshot and video options
        cmd.extend([
            '--capture=no',
            '--tb=short',
        ])

        print("="*80)
        print("Running Playwright Pharmacy Tests")
        print("="*80)
        print(f"Test File: {self.test_file}")
        print(f"Report File: {report_file}")
        print(f"Test Group: {test_group or 'ALL'}")
        print(f"Headless Mode: {headless}")
        print("="*80 + "\n")

        start_time = time.time()

        try:
            result = subprocess.run(cmd, check=False)
            elapsed_time = time.time() - start_time

            print("\n" + "="*80)
            print(f"Tests completed in {elapsed_time:.2f} seconds")
            print("="*80)
            print(f"Report available at: {report_file}")
            print("="*80)

            return result.returncode == 0

        except Exception as e:
            print(f"\n❌ Error running tests: {e}")
            return False

    def run_bulk_store_tests(self):
        """Run bulk store specific tests"""
        return self.run_tests('pharmacy and bulk_store', verbose=True)

    def run_transfer_tests(self):
        """Run transfer specific tests"""
        return self.run_tests('pharmacy and transfer', verbose=True)

    def run_edge_case_tests(self):
        """Run edge case tests"""
        return self.run_tests('pharmacy and (edge_case or error)', verbose=True)

    def run_all_tests(self):
        """Run all pharmacy tests"""
        return self.run_tests('pharmacy', verbose=True, headless=False)

    def run_headless_tests(self):
        """Run tests in headless mode (CI/CD)"""
        return self.run_tests('pharmacy', verbose=False, headless=True)

    def check_server_status(self):
        """Check if Django server is running"""
        import requests
        try:
            response = requests.get('http://localhost:8000/', timeout=5)
            if response.status_code == 200:
                print("✓ Django server is running")
                return True
        except:
            pass

        print("❌ Django server is not running")
        print("\nPlease start the server with:")
        print("  python manage.py runserver")
        return False

    def generate_coverage_report(self):
        """Generate test coverage report"""
        print("\n" + "="*80)
        print("Generating Coverage Report")
        print("="*80)

        cmd = [
            sys.executable, '-m', 'pytest',
            '--cov=pharmacy',
            '--cov-report=html:htmlcov',
            '--cov-report=term',
            self.test_file,
        ]

        subprocess.run(cmd, check=True)
        print("✓ Coverage report generated in htmlcov/")
        print("="*80 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run Playwright tests for HMS Pharmacy System'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all pharmacy tests'
    )

    parser.add_argument(
        '--bulk-store',
        action='store_true',
        help='Run bulk store dashboard tests'
    )

    parser.add_argument(
        '--transfers',
        action='store_true',
        help='Run transfer workflow tests'
    )

    parser.add_argument(
        '--edge-cases',
        action='store_true',
        help='Run edge case and error handling tests'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (for CI/CD)'
    )

    parser.add_argument(
        '--install',
        action='store_true',
        help='Install Playwright browsers'
    )

    parser.add_argument(
        '--check-server',
        action='store_true',
        help='Check if Django server is running'
    )

    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    runner = TestRunner()

    if args.install:
        runner.install_playwright()
        return

    if args.check_server:
        runner.check_server_status()
        return

    if args.coverage:
        runner.generate_coverage_report()
        return

    # Check server status before running tests
    if not args.headless:
        if not runner.check_server_status():
            print("\n⚠ Please start the Django server before running tests")
            print("  python manage.py runserver\n")
            sys.exit(1)

    # Run tests based on arguments
    success = True

    if args.all:
        success = runner.run_all_tests()

    elif args.bulk_store:
        success = runner.run_bulk_store_tests()

    elif args.transfers:
        success = runner.run_transfer_tests()

    elif args.edge_cases:
        success = runner.run_edge_case_tests()

    else:
        # Default: run all tests
        print("No specific test group specified. Running all tests...")
        success = runner.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
