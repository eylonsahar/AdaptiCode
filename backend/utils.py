"""
Utility functions for AdaptiCode system.
"""
import math
from typing import Any, List, Optional
from backend.data.models import TreeNode, ListNode


def compare_outputs(expected: Any, actual: Any, tolerance: float = 1e-9, is_unordered: bool = False) -> bool:
    """
    Compare expected and actual outputs with support for various types.
    
    Args:
        expected: Expected output
        actual: Actual output from user code
        tolerance: Tolerance for floating point comparison
        is_unordered: If True, compare lists as unordered sets
        
    Returns:
        True if outputs match, False otherwise
    """
    # Handle None
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    
    # Handle booleans
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected == actual
    
    # Handle numbers
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if isinstance(expected, float) or isinstance(actual, float):
            return abs(expected - actual) < tolerance
        return expected == actual
    
    # Handle strings
    if isinstance(expected, str) and isinstance(actual, str):
        return expected == actual
    
    # Handle lists (including nested lists)
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
            
        # For unordered comparison (like subsets, permutations)
        if is_unordered:
            # If it's a list of lists, we need to sort each inner list first
            if expected and isinstance(expected[0], list):
                # Sort each inner list and then the outer list
                sorted_expected = sorted(sorted(sublist) for sublist in expected)
                sorted_actual = sorted(sorted(sublist) for sublist in actual)
                return all(compare_outputs(e, a, tolerance) for e, a in zip(sorted_expected, sorted_actual))
            else:
                # For simple lists, just sort and compare
                return sorted(expected) == sorted(actual)
        
        # For ordered comparison
        return all(compare_outputs(e, a, tolerance) for e, a in zip(expected, actual))
    
    # Handle sets (for unordered comparison)
    if isinstance(expected, set) and isinstance(actual, set):
        if len(expected) != len(actual):
            return False
        return expected == actual
    
    # Default equality
    return expected == actual


def normalize_output(output: Any) -> Any:
    """
    Normalize output for comparison.
    
    Handles special cases like sorting lists of lists for unordered comparison.
    """
    if isinstance(output, list):
        # Check if it's a list of lists (like permutations or subsets)
        if output and isinstance(output[0], list):
            # Sort inner lists and outer list for consistent comparison
            return sorted([sorted(inner) if isinstance(inner, list) else inner for inner in output])
        return output
    return output


def format_test_input(test_input: Any) -> str:
    """Format test input for display."""
    if isinstance(test_input, list):
        return str(test_input)
    return str(test_input)


def format_test_output(test_output: Any) -> str:
    """Format test output for display."""
    if isinstance(test_output, list):
        return str(test_output)
    if isinstance(test_output, bool):
        return str(test_output).lower()
    return str(test_output)


def tree_to_list(root: Optional[TreeNode]) -> List[Any]:
    """Convert binary tree to level-order list representation."""
    if root is None:
        return []
    return root.to_list()


def list_to_tree(arr: List[Any]) -> Optional[TreeNode]:
    """Convert level-order list to binary tree."""
    return TreeNode.from_list(arr)


def linkedlist_to_list(head: Optional[ListNode]) -> List[Any]:
    """Convert linked list to array."""
    if head is None:
        return []
    return head.to_list()


def list_to_linkedlist(arr: List[Any]) -> Optional[ListNode]:
    """Convert array to linked list."""
    return ListNode.from_list(arr)


def sigmoid(x: float) -> float:
    """Compute sigmoid function."""
    if x < -500:
        return 0.0
    if x > 500:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def normal_pdf(x: float, mean: float = 0.0, std: float = 1.0) -> float:
    """
    Compute normal probability density function.
    
    Args:
        x: Value to evaluate
        mean: Mean of distribution
        std: Standard deviation
        
    Returns:
        PDF value at x
    """
    variance = std ** 2
    coefficient = 1.0 / math.sqrt(2 * math.pi * variance)
    exponent = -((x - mean) ** 2) / (2 * variance)
    return coefficient * math.exp(exponent)


def logistic(x: float) -> float:
    """Compute logistic function (same as sigmoid)."""
    return sigmoid(x)


def safe_log(x: float, epsilon: float = 1e-10) -> float:
    """Compute log with safety for values near 0."""
    return math.log(max(x, epsilon))


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))

