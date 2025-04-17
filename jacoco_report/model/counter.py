"""
A module that contains the Counter class.
"""

from typing import Union, Optional


# pylint: disable=too-few-public-methods
class Counter:
    """
    A class that represents a counter
    """

    def __init__(self, missed: int, covered: int):
        """
        A constructor for the Counter class

        Parameters:
            missed (int): The number of missed
            covered (int): The number of covered
        """
        self.missed: int = missed
        self.covered: int = covered

    def coverage(self) -> float:
        """
        A method that calculates the coverage

        Returns:
            float: The coverage
        """
        if self.missed + self.covered == 0:
            return 0.0

        return round(self.covered / (self.missed + self.covered) * 100, 2)

    def append(self, missed: Union[int, "Counter"], covered: Optional[int] = None):
        """
        A method that appends the counter.

        Parameters:
            missed (int or Counter): The number of missed OR a Counter object.
            covered (int, optional): The number of covered (only used if missed is an int).
        """
        if isinstance(missed, int) and isinstance(covered, int):
            self.missed += missed
            self.covered += covered
        elif isinstance(missed, Counter):  # Assuming Counter has missed and covered attributes
            self.missed += missed.missed
            self.covered += missed.covered

    def __str__(self):
        """
        Returns the string representation of the Counter class

        Returns:
            str: The string representation of the Counter class
        """
        return f"Missed: {self.missed}, Covered: {self.covered}"

    def __eq__(self, other):
        """
        A method that checks if two Counters are equal

        Parameters:
            other (Counter): The other Counter

        Returns:
            bool: True if the Counters are equal, False otherwise
        """
        return self.missed == other.missed and self.covered == other.covered
