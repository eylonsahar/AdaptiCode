"""
Code Executor for running user-submitted Python code in a sandboxed environment.
"""
import subprocess
import tempfile
import os
import signal
import sys
from typing import Dict, Any, Optional
from backend.config import Config


class CodeExecutor:
    """
    Executes Python code in a sandboxed subprocess environment.
    
    Features:
    - Timeout mechanism
    - Resource limits
    - Capture stdout, stderr
    - Safe execution
    """
    
    def __init__(self):
        """Initialize code executor."""
        self.timeout = Config.CODE_EXECUTION_TIMEOUT
        self.max_memory_mb = Config.MAX_MEMORY_MB
    
    def execute(self, code: str, test_input: Any = None) -> Dict[str, Any]:
        """
        Execute Python code with optional input.
        
        Args:
            code: Python code to execute
            test_input: Optional input to pass to the code
            
        Returns:
            Dictionary with execution results:
            - success: bool
            - output: stdout output
            - error: stderr output
            - return_code: process return code
            - timeout: whether execution timed out
        """
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = f.name
            f.write(code)
        
        try:
            # Prepare the command
            cmd = [sys.executable, temp_file]
            
            # Execute with timeout
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    # Add resource limits on Unix systems
                    preexec_fn=self._set_resource_limits if os.name != 'nt' else None
                )
                
                return {
                    'success': result.returncode == 0,
                    'output': result.stdout,
                    'error': result.stderr,
                    'return_code': result.returncode,
                    'timeout': False
                }
            
            except subprocess.TimeoutExpired:
                return {
                    'success': False,
                    'output': '',
                    'error': f'Execution timed out after {self.timeout} seconds',
                    'return_code': -1,
                    'timeout': True
                }

            except FileNotFoundError as e:
                return {
                    'success': False,
                    'output': '',
                    'error': (
                        f'Failed to start Python interpreter ({sys.executable}). '
                        f'Original error: {str(e)}'
                    ),
                    'return_code': -1,
                    'timeout': False
                }
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def _set_resource_limits(self):
        """Set resource limits for subprocess (Unix only)."""
        try:
            import resource
            
            # Set memory limit
            max_memory_bytes = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
            
            # Set CPU time limit
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout))
        except:
            # If resource module not available or fails, continue without limits
            pass
    
    def execute_with_wrapper(self, user_function: str, function_name: str, 
                            test_input: Any, expected_output: Any = None) -> Dict[str, Any]:
        """
        Execute user function with test wrapper.
        
        Args:
            user_function: User's function code
            function_name: Name of the function to test
            test_input: Input to pass to function
            expected_output: Expected output (optional)
            
        Returns:
            Execution results with actual output
        """
        # Build wrapper code
        wrapper_code = self._build_wrapper_code(
            user_function, 
            function_name, 
            test_input
        )
        
        # Execute
        result = self.execute(wrapper_code)
        
        if result['success']:
            # Parse output
            try:
                # The wrapper prints the result in a parseable format
                output_str = result['output'].strip()
                actual_output = eval(output_str) if output_str else None
                result['actual_output'] = actual_output
                result['matches_expected'] = (actual_output == expected_output) if expected_output is not None else None
            except Exception as e:
                result['success'] = False
                result['error'] = f"Failed to parse output: {str(e)}"
        
        return result
    
    def _build_wrapper_code(self, user_function: str, function_name: str, 
                           test_input: Any) -> str:
        """
        Build wrapper code that includes helper classes and test execution.
        
        Args:
            user_function: User's function code
            function_name: Name of function to call
            test_input: Input to pass to function
            
        Returns:
            Complete Python code ready to execute
        """

        # Build test execution code
        test_code = self._build_test_call(function_name, test_input)
        
        # Combine all parts
        full_code = f"{user_function}\n\n{test_code}"
        
        return full_code
    
    def _build_test_call(self, function_name: str, test_input: Any) -> str:
        """
        Build the test call code.
        
        Args:
            function_name: Function to call
            test_input: Input to pass
            
        Returns:
            Python code to call function and print result
        """
        # Convert test_input to appropriate format
        if isinstance(test_input, list):
            # If the input is a list with a single element that is also a list,
            # pass it as a single argument
            if len(test_input) == 1 and isinstance(test_input[0], list):
                args_str = repr(test_input[0])
            else:
                # Otherwise, pass the list elements as separate arguments
                args_str = ", ".join(repr(arg) for arg in test_input)
        else:
            # For non-list inputs, just use the repr
            args_str = repr(test_input)
        
        code = f'''
# Test execution
try:
    result = {function_name}({args_str})
    
    # Convert result to serializable format
    if hasattr(result, 'to_list'):
        result = result.to_list()
    elif isinstance(result, list) and result and hasattr(result[0], 'to_list'):
        result = [item.to_list() for item in result]
    
    print(repr(result))
except Exception as e:
    import traceback
    print(f"ERROR: {{e}}", file=__import__('sys').stderr)
    traceback.print_exc()
    exit(1)
'''
        return code
    
    def _format_arguments(self, test_input: list) -> str:
        """
        Format test input as function arguments.
        
        Handles cases like:
        - [tree_array, value] -> TreeNode.from_list(tree_array), value
        - [list1, list2] -> ListNode.from_list(list1), ListNode.from_list(list2)
        - [[board], word] -> board, word
        """
        if not test_input:
            return ""
        
        # Heuristic: if first element is a list, might be tree/linked list
        # This is a simplified approach; could be enhanced with metadata
        
        args = []
        for arg in test_input:
            args.append(repr(arg))
        
        return ", ".join(args)
    
    def validate_syntax(self, code: str) -> Dict[str, Any]:
        """
        Validate Python syntax and check for disallowed functions.
        
        Args:
            code: Python code to validate
            
        Returns:
            Dictionary with validation results
        """
        # Check for print statements
        if 'print(' in code:
            return {
                'valid': False,
                'error': "The use of 'print()' is not allowed. Please remove any print statements from your code."
            }
        
        try:
            compile(code, '<string>', 'exec')
            return {
                'valid': True,
                'error': None
            }
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f"Syntax error at line {e.lineno}: {e.msg}"
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

