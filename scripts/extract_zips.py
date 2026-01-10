"""
Safe ZIP extraction script for company data archives.

Extracts all ZIP files from zip_files/ directory into data/ directory,
with each ZIP getting its own subfolder. Handles errors gracefully and
prevents path traversal attacks.
"""
import argparse
import logging
import sys
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from typing import Tuple, List


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the script.
    
    Args:
        verbose: If True, set log level to DEBUG
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def is_safe_path(basedir: Path, path: str) -> bool:
    """
    Check if a path is safe (no path traversal attacks).
    
    Args:
        basedir: Base directory for extraction
        path: Path to validate
        
    Returns:
        True if path is safe, False otherwise
    """
    # Resolve the full path and check it's within basedir
    try:
        full_path = (basedir / path).resolve()
        return full_path.is_relative_to(basedir.resolve())
    except (ValueError, OSError):
        return False


def extract_zip_safely(
    zip_path: Path,
    target_dir: Path,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Safely extract a ZIP file to target directory.
    
    Args:
        zip_path: Path to ZIP file
        target_dir: Directory to extract into
        force: If True, overwrite existing extraction
        
    Returns:
        Tuple of (success, message)
    """
    logger = logging.getLogger(__name__)
    
    # Determine extraction folder name (ZIP name without .zip)
    extract_folder = target_dir / zip_path.stem
    
    # Check if already extracted
    if extract_folder.exists() and not force:
        return False, f"Already extracted (use --force to re-extract)"
    
    # Create extraction folder
    try:
        extract_folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return False, f"Failed to create directory: {e}"
    
    # Extract ZIP file
    try:
        with ZipFile(zip_path, 'r') as zip_file:
            # Validate all paths before extraction
            for member in zip_file.namelist():
                if not is_safe_path(extract_folder, member):
                    return False, f"Unsafe path detected in ZIP: {member}"
            
            # Extract all files
            zip_file.extractall(extract_folder)
            
            # Count extracted files
            file_count = len(zip_file.namelist())
            return True, f"Extracted {file_count} files successfully"
            
    except BadZipFile:
        return False, "Corrupted or invalid ZIP file"
    except Exception as e:
        return False, f"Extraction failed: {type(e).__name__}: {e}"


def process_all_zips(
    zip_dir: Path,
    data_dir: Path,
    force: bool = False
) -> Tuple[int, int, int]:
    """
    Process all ZIP files in the zip directory.
    
    Args:
        zip_dir: Directory containing ZIP files
        data_dir: Directory to extract into
        force: If True, re-extract existing folders
        
    Returns:
        Tuple of (extracted_count, skipped_count, failed_count)
    """
    logger = logging.getLogger(__name__)
    
    # Validate zip directory exists
    if not zip_dir.exists():
        logger.error(f"ZIP directory does not exist: {zip_dir}")
        return 0, 0, 0
    
    # Create data directory if needed
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all ZIP files
    zip_files = sorted(zip_dir.glob("*.zip"))
    
    if not zip_files:
        logger.warning(f"No ZIP files found in {zip_dir}")
        return 0, 0, 0
    
    logger.info(f"Found {len(zip_files)} ZIP files to process")
    logger.info("=" * 80)
    
    extracted_count = 0
    skipped_count = 0
    failed_count = 0
    
    for i, zip_path in enumerate(zip_files, 1):
        logger.info(f"[{i}/{len(zip_files)}] Processing: {zip_path.name}")
        
        success, message = extract_zip_safely(zip_path, data_dir, force)
        
        if success:
            extracted_count += 1
            logger.info(f"  ✓ {message}")
        elif "Already extracted" in message:
            skipped_count += 1
            logger.info(f"  ⊘ {message}")
        else:
            failed_count += 1
            logger.error(f"  ✗ {message}")
    
    return extracted_count, skipped_count, failed_count


def main() -> int:
    """
    Main entry point for the ZIP extraction script.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Extract company data ZIP archives safely",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_zips.py
  python extract_zips.py --force
  python extract_zips.py --zip-dir custom_zips --data-dir custom_data
  python extract_zips.py --verbose
        """
    )
    
    parser.add_argument(
        '--zip-dir',
        type=Path,
        default=Path('zip_files'),
        help='Directory containing ZIP files (default: zip_files)'
    )
    
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('data'),
        help='Directory to extract files into (default: data)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-extraction of already extracted folders'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Log configuration
    logger.info("ZIP Extraction Script")
    logger.info("=" * 80)
    logger.info(f"ZIP directory: {args.zip_dir.absolute()}")
    logger.info(f"Data directory: {args.data_dir.absolute()}")
    logger.info(f"Force re-extraction: {args.force}")
    logger.info("")
    
    # Process all ZIP files
    try:
        extracted, skipped, failed = process_all_zips(
            args.zip_dir,
            args.data_dir,
            args.force
        )
        
        # Print summary
        logger.info("=" * 80)
        logger.info("Extraction Summary:")
        logger.info(f"  Extracted: {extracted}")
        logger.info(f"  Skipped:   {skipped}")
        logger.info(f"  Failed:    {failed}")
        logger.info(f"  Total:     {extracted + skipped + failed}")
        
        if failed > 0:
            logger.warning(f"{failed} ZIP file(s) failed to extract")
            return 1
        
        logger.info("All ZIP files processed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Extraction interrupted by user")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
