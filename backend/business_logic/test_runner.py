"""
Test Runner for executing tests against user code.
"""
from typing import Dict, List, Any, Tuple
from backend.data.models import Question, Test
from backend.business_logic.code_executor import CodeExecutor
from backend.utils import compare_outputs, format_test_input, format_test_output


class TestRunner:
    """
    Runs tests against user-submitted code.
    
    Executes both visible and hidden tests, compares outputs,
    and provides detailed feedback.
    """
    
    def __init__(self):
        """Initialize test runner."""
        self.executor = CodeExecutor()
    
    def run_tests(self, code: str, question: Question, 
                  include_hidden: bool = True) -> Dict[str, Any]:
        """
        Run all tests for a question.
        
        Args:
            code: User's code
            question: Question with test cases
            include_hidden: Whether to run hidden tests
            
        Returns:
            Dictionary with test results
        """
        # First validate syntax
        validation = self.executor.validate_syntax(code)
        if not validation['valid']:
            return {
                'success': False,
                'syntax_error': validation['error'],
                'visible_tests': [],
                'hidden_tests': [],
                'total_tests': 0,
                'passed_tests': 0,
                'all_passed': False
            }
        
        # Expect a user-defined function named "solve" in the code. This keeps
        # the mental model for learners simple: always implement your answer in
        # a function called `solve`.
        function_name = 'solve'
        if 'def solve' not in code:
            return {
                'success': False,
                'error': 'Please define your solution in a function named "solve".',
                'visible_tests': [],
                'hidden_tests': [],
                'total_tests': 0,
                'passed_tests': 0,
                'all_passed': False
            }
        
        # Run visible tests
        visible_results = self._run_test_set(code, function_name, question.tests, visible=True)
        
        # Run hidden tests if requested
        hidden_results = []
        if include_hidden:
            hidden_results = self._run_test_set(code, function_name, question.hidden_tests, visible=False)
        
        # Calculate statistics
        total_tests = len(visible_results) + len(hidden_results)
        passed_tests = sum(1 for r in visible_results if r['passed']) + \
                      sum(1 for r in hidden_results if r['passed'])
        
        all_passed = (passed_tests == total_tests) if total_tests > 0 else False
        
        return {
            'success': True,
            'function_name': function_name,
            'visible_tests': visible_results,
            'hidden_tests': hidden_results,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'all_passed': all_passed,
            'pass_rate': passed_tests / total_tests if total_tests > 0 else 0.0
        }
    
    def _run_test_set(self, code: str, function_name: str, 
                     tests: List[Test], visible: bool) -> List[Dict]:
        """
        Run a set of tests.
        
        Args:
            code: User's code
            function_name: Name of function to test
            tests: List of test cases
            visible: Whether these are visible tests
            
        Returns:
            List of test results
        """
        results = []
        
        for i, test in enumerate(tests):
            result = self._run_single_test(code, function_name, test, i, visible)
            results.append(result)
        
        return results
    
    def _run_single_test(self, code: str, function_name: str, 
                        test: Test, test_num: int, visible: bool) -> Dict:
        """
        Run a single test case.
        
        Args:
            code: User's code
            function_name: Function to test
            test: Test case
            test_num: Test number
            visible: Whether this is a visible test
            
        Returns:
            Test result dictionary
        """
        # Check if this test should use unordered comparison
        is_unordered = getattr(test, 'is_unordered', False)
        
        # Execute the test
        exec_result = self.executor.execute_with_wrapper(
            code,
            function_name,
            test.input,
            test.output
        )
        
        # Determine if test passed
        passed = False
        actual_output = None
        error_message = None
        
        if exec_result['success']:
            actual_output = exec_result.get('actual_output')
            
            # Compare outputs with is_unordered flag
            try:
                passed = compare_outputs(test.output, actual_output, is_unordered=is_unordered)
            except Exception as e:
                error_message = f"Comparison error: {str(e)}"
        else:
            error_message = exec_result.get('error', 'Execution failed')
        
        # Build result
        result = {
            'test_num': test_num + 1,
            'visible': visible,
            'passed': passed,
            'timeout': exec_result.get('timeout', False)
        }
        
        # Include details for visible tests or if failed
        if visible or not passed:
            result['input'] = format_test_input(test.input)
            result['expected_output'] = format_test_output(test.output)
            
            if actual_output is not None:
                result['actual_output'] = format_test_output(actual_output)
            
            if error_message:
                result['error'] = error_message
        
        return result
    
    def _extract_function_name(self, code: str) -> str:
        """
        Extract function name from code.
        
        Looks for 'def function_name(' pattern.
        
        Args:
            code: Python code
            
        Returns:
            Function name or empty string
        """
        import re
        
        # Look for function definition
        match = re.search(r'def\s+(\w+)\s*\(', code)
        
        if match:
            return match.group(1)
        
        return ""
    
    def run_quick_test(self, code: str, function_name: str, 
                      test_input: Any, expected_output: Any = None) -> Dict:
        """
        Run a quick single test (for testing/debugging).
        
        Args:
            code: User's code
            function_name: Function to test
            test_input: Input to test with
            expected_output: Expected output (optional)
            
        Returns:
            Test result
        """
        exec_result = self.executor.execute_with_wrapper(
            code,
            function_name,
            test_input,
            expected_output
        )
        
        return exec_result
    
    def get_test_summary(self, test_results: Dict) -> str:
        """
        Generate human-readable test summary.
        
        Args:
            test_results: Results from run_tests
            
        Returns:
            Summary string
        """
        if not test_results.get('success'):
            if 'syntax_error' in test_results:
                return f"Syntax Error: {test_results['syntax_error']}"
            return f"Error: {test_results.get('error', 'Unknown error')}"
        
        passed = test_results['passed_tests']
        total = test_results['total_tests']
        
        if test_results['all_passed']:
            return f"✓ All tests passed! ({passed}/{total})"
        else:
            failed = total - passed
            return f"✗ {failed} test(s) failed. Passed: {passed}/{total}"
    
    def get_detailed_feedback(self, test_results: Dict) -> List[str]:
        """
        Generate detailed feedback messages.
        
        Args:
            test_results: Results from run_tests
            
        Returns:
            List of feedback messages
        """
        feedback = []
        
        if not test_results.get('success'):
            return [test_results.get('error', 'Unknown error')]
        
        # Feedback on visible tests
        for test in test_results['visible_tests']:
            if not test['passed']:
                msg = f"Test {test['test_num']} failed:\n"
                msg += f"  Input: {test['input']}\n"
                msg += f"  Expected: {test['expected_output']}\n"
                
                if 'actual_output' in test:
                    msg += f"  Got: {test['actual_output']}\n"
                
                if 'error' in test:
                    msg += f"  Error: {test['error']}\n"
                
                feedback.append(msg)
        
        # Feedback on hidden tests (less detailed)
        hidden_failed = sum(1 for t in test_results['hidden_tests'] if not t['passed'])
        if hidden_failed > 0:
            feedback.append(
                f"{hidden_failed} hidden test(s) failed. "
                "These tests check edge cases and special conditions."
            )
        
        return feedback
    
    def calculate_code_quality_score(self, test_results: Dict, time_taken: float) -> float:
        """
        Calculate a code quality score based on test results and time.
        
        Args:
            test_results: Test results
            time_taken: Time taken to solve (seconds)
            
        Returns:
            Quality score (0-1)
        """
        if not test_results.get('success'):
            return 0.0
        
        # Base score from pass rate
        pass_rate = test_results.get('pass_rate', 0.0)
        
        # Time bonus (faster is better, but with diminishing returns)
        # Normalize time to 0-1 scale (assuming 300s = 5min is reasonable)
        time_factor = max(0, 1 - (time_taken / 300))
        time_bonus = time_factor * 0.2  # Up to 20% bonus for speed
        
        # Combine
        quality_score = min(1.0, pass_rate + time_bonus)
        
        return quality_score

