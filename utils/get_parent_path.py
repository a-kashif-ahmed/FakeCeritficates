from pathlib import Path

# Returns the parent directory of this file (i.e., utils directory’s parent, which is the project root)

def get_parent_path() -> Path:
    return Path(__file__).parent.parent
