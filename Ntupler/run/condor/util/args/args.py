import argparse
import glob
import re
from pathlib import Path

class FileListAction(argparse.Action):
    """
    Custom argparse action for parsing file paths in multiple formats:
    - List of strings (nargs='+')
    - Glob pattern (e.g., 'data/*.root')
    - Delimiter-separated string (e.g., 'a.root;b.root' or 'a.root, b.root')
    - Text file with newline-separated paths (e.g., 'files.txt')
      - For .txt files, paths are prepended with 'root://cms-xrd-global.cern.ch/'

    Supports various delimiters: comma, semicolon, pipe, colon, and whitespace.
    """

    # Common delimiters for splitting file lists
    DELIMITERS = r'[,;|\s:]+'
    XROOTD_PREFIX = 'root://cms-xrd-global.cern.ch/'

    def __call__(self, parser, namespace, values, option_string=None):
        """
        Process the input values and store the resulting file list.

        Args:
            parser: ArgumentParser instance
            namespace: Namespace object to store results
            values: Input value(s) from command line
            option_string: Option string used (e.g., '--files')
        """
        file_list = []

        # Handle case where values is already a list (nargs='+')
        if isinstance(values, list):
            for item in values:
                file_list.extend(self._parse_single_value(item))
        else:
            # Single string value
            file_list = self._parse_single_value(values)

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in file_list:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        setattr(namespace, self.dest, unique_files)

    def _parse_single_value(self, value):
        """
        Parse a single value that could be:
        - A .txt file containing newline-separated paths
        - A glob pattern
        - A delimiter-separated list
        - A single file path

        Args:
            value: String to parse

        Returns:
            List of file paths
        """

        # Check if this is a .txt file
        if value.endswith('.txt'):
            return self._parse_txt_file(value)

        # First, try glob expansion
        glob_matches = glob.glob(value)
        if glob_matches:
            # Sort for consistent ordering
            return sorted(glob_matches)

        # Check if value contains delimiters
        if re.search(self.DELIMITERS, value):
            # Split by delimiters and strip whitespace
            parts = re.split(self.DELIMITERS, value)
            files = [p.strip() for p in parts if p.strip()]

            # Recursively process each part (in case they're globs)
            result = []
            for part in files:
                expanded = glob.glob(part)
                if expanded:
                    result.extend(sorted(expanded))
                else:
                    result.append(part)
            return result

        # Single file path (might not exist yet)
        return [value]

    def _parse_txt_file(self, filepath):
        """
        Parse a .txt file containing newline-separated file paths.
        Prepends XRootD prefix to each path.

        Args:
            filepath: Path to .txt file

        Returns:
            List of file paths with XRootD prefix

        Raises:
            FileNotFoundError: If the .txt file doesn't exist
            ValueError: If the .txt file is empty
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {filepath}")

        with open(path, 'r') as f:
            lines = f.readlines()

        # Strip whitespace and filter out empty lines and comments
        files = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and lines starting with #
            if line and not line.startswith('#'):
                # Prepend XRootD prefix if not already present
                if not line.startswith('root://'):
                    line = self.XROOTD_PREFIX + line
                files.append(line)

        if not files:
            raise ValueError(f"Text file contains no valid file paths: {filepath}")

        return files