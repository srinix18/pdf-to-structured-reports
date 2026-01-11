"""
Section boundary detector - analyzes PDF layout to identify section boundaries.
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pdfplumber

from pipeline.section_metadata import (
    TextBlock, SectionBoundary, SectionType, 
    SECTION_KEYWORDS, SECTION_END_KEYWORDS
)

logger = logging.getLogger(__name__)


class SectionBoundaryDetector:
    """
    Detects section boundaries from PDF layout metadata.
    Uses font size, position, and keyword matching.
    """
    
    def __init__(self, pdf_path: Path):
        """
        Initialize detector with PDF path.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.text_blocks: List[TextBlock] = []
        
    def extract_layout_metadata(self) -> List[TextBlock]:
        """
        Extract text blocks with layout metadata from PDF.
        
        Returns:
            List of TextBlock objects with font size and position info
        """
        logger.info(f"Extracting layout metadata from {self.pdf_path.name}")
        blocks = []
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text with layout information
                    words = page.extract_words(
                        x_tolerance=3,
                        y_tolerance=3,
                        keep_blank_chars=False
                    )
                    
                    if not words:
                        continue
                    
                    # Calculate median font size for this page
                    font_sizes = [w.get('height', 10) for w in words]
                    page_median_font = sorted(font_sizes)[len(font_sizes) // 2] if font_sizes else 10
                    
                    # Group words into lines based on y-position
                    lines = self._group_words_into_lines(words)
                    
                    for line in lines:
                        text = ' '.join([w['text'] for w in line])
                        
                        if not text.strip():
                            continue
                        
                        # Use first word's metrics as line metrics
                        first_word = line[0]
                        font_size = first_word.get('height', page_median_font)
                        y_pos = first_word['top']
                        x_pos = first_word['x0']
                        
                        # Bounding box for entire line
                        x0 = min(w['x0'] for w in line)
                        y0 = min(w['top'] for w in line)
                        x1 = max(w['x1'] for w in line)
                        y1 = max(w['bottom'] for w in line)
                        
                        block = TextBlock(
                            text=text,
                            page_number=page_num,
                            font_size=font_size,
                            y_position=y_pos,
                            x_position=x_pos,
                            bbox=(x0, y0, x1, y1)
                        )
                        blocks.append(block)
                        
        except Exception as e:
            logger.error(f"Error extracting layout metadata: {e}", exc_info=True)
        
        logger.info(f"Extracted {len(blocks)} text blocks from {page_num} pages")
        self.text_blocks = blocks
        return blocks
    
    def _group_words_into_lines(self, words: List[dict]) -> List[List[dict]]:
        """
        Group words into lines based on y-position proximity.
        
        Args:
            words: List of word dictionaries from pdfplumber
            
        Returns:
            List of lines, where each line is a list of words
        """
        if not words:
            return []
        
        # Sort by y-position, then x-position
        sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
        
        lines = []
        current_line = [sorted_words[0]]
        current_y = sorted_words[0]['top']
        
        for word in sorted_words[1:]:
            # If word is on same line (within 3 pixels), add to current line
            if abs(word['top'] - current_y) <= 3:
                current_line.append(word)
            else:
                # Start new line
                lines.append(current_line)
                current_line = [word]
                current_y = word['top']
        
        # Don't forget last line
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def detect_section_boundaries(self) -> Dict[str, Optional[SectionBoundary]]:
        """
        Detect MD&A and Letter to Stakeholders boundaries.
        
        Returns:
            Dictionary mapping section type to SectionBoundary (or None if not found)
        """
        logger.info("Detecting section boundaries...")
        
        if not self.text_blocks:
            self.extract_layout_metadata()
        
        boundaries = {
            "mdna": None,
            "letter_to_stakeholders": None
        }
        
        # Detect each section type
        for section_type in [SectionType.MDNA, SectionType.LETTER_TO_STAKEHOLDERS]:
            boundary = self._find_section_boundary(section_type)
            if boundary:
                boundaries[section_type.value] = boundary
                logger.info(
                    f"Found {section_type.value}: pages {boundary.start_page}-{boundary.end_page}, "
                    f"confidence={boundary.confidence:.2f}"
                )
        
        return boundaries
    
    def _find_section_boundary(self, section_type: SectionType) -> Optional[SectionBoundary]:
        """
        Find boundary for a specific section type.
        
        Args:
            section_type: Type of section to find
            
        Returns:
            SectionBoundary if found, None otherwise
        """
        keywords = SECTION_KEYWORDS.get(section_type, [])
        
        # Find candidate headings
        candidates = []
        
        for block in self.text_blocks:
            # Check if this looks like a heading (pass section_type for context)
            if not self._is_potential_heading(block, section_type):
                continue
            
            # Check if text matches section keywords
            normalized = block.normalized_text
            
            for keyword in keywords:
                if keyword in normalized:
                    confidence = self._calculate_confidence(block, keyword, normalized, section_type)
                    candidates.append((block, confidence, keyword))
                    logger.debug(
                        f"Candidate heading on page {block.page_number}: "
                        f"'{block.text}' (confidence={confidence:.2f})"
                    )
                    break
        
        if not candidates:
            logger.info(f"No candidates found for {section_type.value}")
            return None
        
        # Select best candidate (highest confidence)
        best_block, best_confidence, matched_keyword = max(candidates, key=lambda x: x[1])
        
        # Find section end
        end_page = self._find_section_end(best_block.page_number, section_type)
        
        return SectionBoundary(
            section_type=section_type,
            start_page=best_block.page_number,
            end_page=end_page,
            confidence=best_confidence,
            start_heading=best_block.text,
            detection_method="layout_and_keywords"
        )
    
    def _is_potential_heading(self, block: TextBlock, section_type: Optional[SectionType] = None) -> bool:
        """
        Check if text block could be a section heading.
        
        Criteria vary by section type:
        - MD&A: Strict criteria (top of page, large font)
        - Letter: More lenient (can be anywhere, moderate font)
        
        Args:
            block: TextBlock to evaluate
            section_type: Optional section type for context-specific rules
            
        Returns:
            True if block could be a heading
        """
        # Line length check - headings are typically short
        if block.line_length > 150:
            return False
        
        # Get page median font size for comparison
        page_blocks = [b for b in self.text_blocks if b.page_number == block.page_number]
        if not page_blocks:
            return False
        
        page_fonts = [b.font_size for b in page_blocks]
        median_font = sorted(page_fonts)[len(page_fonts) // 2]
        
        # Letter sections can appear anywhere in early pages (industry standard)
        # In most annual reports, letters are within first 15-20 pages
        if section_type == SectionType.LETTER_TO_STAKEHOLDERS:
            # More lenient for letters - they often appear in first 20 pages
            # This range covers 95%+ of letters in typical annual reports
            if block.page_number > 20:
                return False
            
            # Letter headings can be anywhere on page (not just top)
            # Often positioned mid-page with decorative layouts
            # Should have EITHER: slight font prominence (1.05x) OR be very short (<50 chars)
            # The 1.05x threshold catches letters with subtle formatting differences
            if block.font_size >= median_font * 1.05 or block.line_length < 50:
                return True
            
            return False
        
        # MD&A sections: stricter criteria (must be prominent heading at top of page)
        # These sections typically have clear, prominent headings in standard locations
        else:
            # Y-position check (top 40% of typical page ~800pts = top 320-350pts)
            # This threshold works across different page sizes and layouts
            if block.y_position > 350:
                return False
            
            # Font should be noticeably larger than median (1.1x minimum)
            # More strict than letters to avoid false positives in body text
            if block.font_size < median_font * 1.1:
                return False
        
        return True
    
    def _calculate_confidence(self, block: TextBlock, keyword: str, normalized_text: str, 
                             section_type: Optional[SectionType] = None) -> float:
        """
        Calculate confidence score for a heading match.
        
        Factors:
        - Keyword match quality (exact vs partial)
        - Font size prominence
        - Y-position (prefer higher on page for MD&A, less important for letters)
        - Line length (prefer shorter)
        - Section type specific adjustments
        
        Args:
            block: Detected text block
            keyword: Matched keyword
            normalized_text: Normalized block text
            section_type: Type of section being detected
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.5  # Base confidence
        
        # Keyword match quality
        if normalized_text.strip() == keyword:
            confidence += 0.3  # Exact match
        elif normalized_text.startswith(keyword) or normalized_text.endswith(keyword):
            confidence += 0.2  # Strong match
        else:
            confidence += 0.1  # Partial match
        
        # Font size prominence (get page median)
        page_blocks = [b for b in self.text_blocks if b.page_number == block.page_number]
        if page_blocks:
            page_fonts = [b.font_size for b in page_blocks]
            median_font = sorted(page_fonts)[len(page_fonts) // 2]
            font_ratio = block.font_size / median_font if median_font > 0 else 1
            
            if font_ratio > 1.5:
                confidence += 0.15
            elif font_ratio > 1.2:
                confidence += 0.1
            elif font_ratio > 1.05:
                confidence += 0.05
        
        # Position bonus - different for different section types
        if section_type == SectionType.LETTER_TO_STAKEHOLDERS:
            # For letters, early pages are better (less strict on y-position)
            if block.page_number <= 10:
                confidence += 0.1
            elif block.page_number <= 15:
                confidence += 0.05
        else:
            # For MD&A, y-position matters more
            if block.y_position < 150:
                confidence += 0.1
            elif block.y_position < 250:
                confidence += 0.05
        
        # Line length bonus (shorter is better for headings)
        if block.line_length < 40:
            confidence += 0.05
        elif block.line_length < 60:
            confidence += 0.03
        
        return min(confidence, 1.0)
    
    def _find_section_end(self, start_page: int, section_type: SectionType) -> Optional[int]:
        """
        Find where a section ends.
        
        End detection:
        - Another major heading appears
        - Financial statement keywords appear
        - Structural sections (board report, annual return, etc)
        - For letters: typically short (5-20 pages)
        - End of document
        
        Args:
            start_page: Page where section starts
            section_type: Type of section
            
        Returns:
            End page number or None if continues to document end
        """
        # Look for end indicators after start page
        subsequent_blocks = [b for b in self.text_blocks if b.page_number > start_page]
        
        # Additional keywords that typically mark end of narrative sections
        structural_keywords = [
            "extract of annual return",
            "annual return",
            "board report",
            "directors report",
            "director's report",
            "directors' report",
            "corporate governance",
            "corporate information",
            "company information",
            "particulars of employees",
            "form no.",
            "annexure",
            "schedules to",
            "notes forming part",
            "significant accounting policies",
            "disclosures under",
            "statutory section"
        ]
        
        # New section transition keywords (common in annual reports across industries)
        # These mark the transition from narrative sections to business/financial content
        new_section_keywords = [
            "key financial highlights",
            "financial highlights",
            "wealth creation",
            "wealth preservation",
            "performance highlights",
            "business overview",
            "our business",
            "segment performance",
            "operational highlights",
            "strategic priorities",
            "board of directors"
        ]
        
        # For letters, track pages to detect consistent new section headings
        last_heading_page = start_page
        
        for block in subsequent_blocks:
            normalized = block.normalized_text
            
            # Check for financial statement keywords
            for end_keyword in SECTION_END_KEYWORDS:
                if end_keyword in normalized and self._is_potential_heading(block, None):
                    logger.debug(
                        f"Section end detected at page {block.page_number}: "
                        f"'{block.text}' (financial statement keyword)"
                    )
                    return block.page_number - 1
            
            # Check for structural section markers (especially important for letters)
            if section_type == SectionType.LETTER_TO_STAKEHOLDERS:
                for struct_keyword in structural_keywords:
                    if struct_keyword in normalized and self._is_potential_heading(block, None):
                        logger.debug(
                            f"Section end detected at page {block.page_number}: "
                            f"'{block.text}' (structural keyword)"
                        )
                        return block.page_number - 1
                
                # Check for new section transitions (big headings that mark letter end)
                # Look for keywords with prominent font size (industry standard approach)
                for new_keyword in new_section_keywords:
                    if new_keyword in normalized and self._is_potential_heading(block, None):
                        # Get page fonts to calculate median
                        page_fonts = [b.font_size for b in self.text_blocks 
                                    if b.page_number == block.page_number and b.font_size > 0]
                        median_font = sorted(page_fonts)[len(page_fonts) // 2] if page_fonts else 10
                        
                        # Big heading = significant font size (1.5x+ median) - indicates new section
                        # This ratio is conservative and works across different PDF styles
                        if block.font_size >= median_font * 1.5:
                            logger.debug(
                                f"Section end detected at page {block.page_number}: "
                                f"'{block.text}' (new section heading, {block.font_size:.1f}pt)"
                            )
                            return block.page_number - 1
                
                # For letters: any prominent new heading after a few pages marks transition
                # Skip if we're still near the start (within 3 pages) to avoid false positives
                # This is a fallback for headings not caught by keyword matching
                if block.page_number > start_page + 3:
                    page_fonts = [b.font_size for b in self.text_blocks 
                                if b.page_number == block.page_number and b.font_size > 0]
                    median_font = sorted(page_fonts)[len(page_fonts) // 2] if page_fonts else 10
                    
                    # Big standalone heading (1.8x+ median, short line < 50 chars)
                    # The 1.8x ratio is more aggressive to catch very prominent section breaks
                    # Requires gap from last heading to avoid detecting subsections
                    if (self._is_potential_heading(block, None) and 
                        block.font_size >= median_font * 1.8 and
                        block.line_length < 50 and
                        block.page_number > last_heading_page + 1):
                        logger.debug(
                            f"Section end detected at page {block.page_number}: "
                            f"'{block.text}' (prominent new heading, {block.font_size:.1f}pt)"
                        )
                        return block.page_number - 1
                
                # Letters are typically short (5-20 pages in most annual reports)
                # If beyond 25 pages, likely entered other sections - look for any major heading
                if block.page_number > start_page + 25:
                    if self._is_potential_heading(block, None) and block.line_length < 80:
                        logger.debug(
                            f"Section end detected at page {block.page_number}: "
                            f"'{block.text}' (letter length limit)"
                        )
                        return block.page_number - 1
            
            # Track headings for letter detection
            if section_type == SectionType.LETTER_TO_STAKEHOLDERS and self._is_potential_heading(block, None):
                last_heading_page = block.page_number
            
            # Check for other major section headings
            for other_type in [SectionType.MDNA, SectionType.LETTER_TO_STAKEHOLDERS]:
                if other_type == section_type:
                    continue
                
                other_keywords = SECTION_KEYWORDS.get(other_type, [])
                for keyword in other_keywords:
                    if keyword in normalized and self._is_potential_heading(block, other_type):
                        logger.debug(
                            f"Section end detected at page {block.page_number}: "
                            f"'{block.text}' (other section start)"
                        )
                        return block.page_number - 1
        
        # If no end found, section continues to end of document
        if subsequent_blocks:
            last_page = max(b.page_number for b in subsequent_blocks)
            return last_page
        
        return start_page  # Single page section
