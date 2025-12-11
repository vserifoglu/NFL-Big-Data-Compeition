import os
import argparse

class FileCombiner:
    """
    A class to combine files from one or more directories into a single flat text file.
    Follows OOP principles, modular design, and DRY by encapsulating traversal and writing logic.
    """
    
    def __init__(self, directories, output_file, ignored_dirs=None):
        """
        Initialize the FileCombiner.
        
        :param directories: List of directory paths to process.
        :param output_file: Path to the output text file.
        :param ignored_dirs: List of directory names to ignore (e.g., '__pycache__').
        """
        self.directories = [os.path.abspath(d) for d in directories]
        self.output_file = os.path.abspath(output_file)
        self.ignored_dirs = ignored_dirs or ['__pycache__', '.pytest_cache', '.git', '.svn', '.hg', '.bzr', '.tox', '.venv', 'build', 'dist']
    
    def combine_files(self):
        """
        Traverse the directories recursively, read text files, and write to the output file.
        Skips ignored directories and binary files (non-UTF-8 decodable).
        """
        with open(self.output_file, 'w', encoding='utf-8') as out_file:
            for root_dir in self.directories:
                self._process_directory(root_dir, out_file, root_dir)
    
    def _process_directory(self, current_dir, out_file, root_dir):
        """
        Recursively process a directory, writing file contents to the output.
        
        :param current_dir: Current directory path being processed.
        :param out_file: Open file handle for writing output.
        :param root_dir: The root directory for relative path calculation.
        """
        for entry in os.scandir(current_dir):
            if entry.is_dir():
                if entry.name in self.ignored_dirs:
                    continue
                self._process_directory(entry.path, out_file, root_dir)
            else:
                self._write_file_content(entry.path, out_file, root_dir)
    
    def _write_file_content(self, file_path, out_file, root_dir):
        """
        Read a file's content and write it to the output with header and separator.
        Skips if file cannot be read as UTF-8 text.
        
        :param file_path: Path to the file to read.
        :param out_file: Open file handle for writing output.
        :param root_dir: The root directory for relative path calculation.
        """
        rel_path = os.path.relpath(file_path, root_dir)
        try:
            with open(file_path, 'r', encoding='utf-8') as in_file:
                content = in_file.read()
            
            separator = "=" * 80
            out_file.write(f"{separator}\n")
            out_file.write(f"File Path: {rel_path}\n")
            out_file.write(f"{separator}\n\n")
            out_file.write(content)
            out_file.write("\n\n")
            out_file.write(f"{separator}\n")
            out_file.write(f"End of File: {rel_path}\n")
            out_file.write(f"{separator}\n\n")
        
        except UnicodeDecodeError:
            # Skip binary files silently
            pass
        except Exception as e:
            # Log error to console but continue
            print(f"Error processing file {rel_path}: {str(e)}")

def main():
    """
    Entry point: Parse command-line arguments and run the combiner.
    """
    parser = argparse.ArgumentParser(
        description="Combine files from directories into a single text file."
    )
    parser.add_argument(
        'directories',
        nargs='+',
        help="One or more directory paths to process."
    )
    parser.add_argument(
        '-o', '--output',
        default='llm_knowledge_base/files_combined.txt',
        help="Path to the output file (default: combined.txt)."
    )
    
    args = parser.parse_args()
    
    combiner = FileCombiner(args.directories, args.output)
    combiner.combine_files()
    print(f"Combined files written to: {args.output}")

if __name__ == "__main__":
    main()