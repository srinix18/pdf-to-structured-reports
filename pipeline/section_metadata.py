"""
Data structures for section metadata and boundaries.
"""
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class SectionType(Enum):
    """Enumeration of supported section types."""
    MDNA = "mdna"
    LETTER_TO_STAKEHOLDERS = "letter_to_stakeholders"
    UNKNOWN = "unknown"


@dataclass
class TextBlock:
    """
    Represents a text block extracted from PDF with layout metadata.
    """
    text: str
    page_number: int
    font_size: float
    y_position: float
    x_position: float
    bbox: tuple  # (x0, y0, x1, y1)
    
    @property
    def normalized_text(self) -> str:
        """Return lowercase text with punctuation removed."""
        import re
        text = self.text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = ' '.join(text.split())
        return text
    
    @property
    def line_length(self) -> int:
        """Return character count of the text."""
        return len(self.text)


@dataclass
class SectionBoundary:
    """
    Represents detected section boundaries with confidence score.
    """
    section_type: SectionType
    start_page: int
    end_page: Optional[int]
    confidence: float
    start_heading: str
    detection_method: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "section_type": self.section_type.value,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "confidence": round(self.confidence, 3),
            "start_heading": self.start_heading,
            "detection_method": self.detection_method
        }


@dataclass
class SectionContent:
    """
    Represents extracted section content.
    """
    section_type: SectionType
    start_page: int
    end_page: int
    text: str
    character_count: int
    page_count: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "section_type": self.section_type.value,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "character_count": self.character_count,
            "page_count": self.page_count
        }


# Canonical keyword patterns for section detection
SECTION_KEYWORDS = {
    SectionType.MDNA: [
        # Full form variations
        "management discussion and analysis",
        "management's discussion and analysis",
        "managements discussion and analysis",
        "management discussion & analysis",
        "management's discussion & analysis",
        "managements discussion & analysis",
        "management discussion",  # Standalone (found in reports)
        "management discussion and",  # Incomplete pattern
        
        # Abbreviations
        "md&a",
        "md & a",
        "md and a",
        "md a",
        "mda",
        
        # Financial review variations
        "financial review",
        "financial performance review",
        "review of financial performance",
        "financial performance",
        "financial position & performance",
        "financial position and performance",
        "financial performance highlights",
        "financial performance overview",
        "financial performance ratios",
        "discussion on financial performance",
        "discussions on financial performance",
        "key highlights financial performance",
        "our financial performance",
        "robust financial performance",
        "strong cross cycle financial performance",
        "strong cross-cycle financial performance",
        "10 year financial performance",
        "10-year financial performance",
        
        # Business/operational review
        "business review",
        "business segment review",
        "operational review",
        "review of operations",
        "performance review",
        "performance a review",
        "performance: a review",
        
        # Other variations found in reports
        "non financial performance",
        "non-financial performance"
    ],
    SectionType.LETTER_TO_STAKEHOLDERS: [
        # Letter headings
        "letter to stakeholders",
        "letter to shareholders",
        "letter from stakeholders",
        "letter from shareholders",
        "letter from chairman",
        "letter from the chairman",
        "letter from ceo",
        "letter from the ceo",
        "letter from md",
        "letter from the md",
        "letter from managing director",
        "letter from the managing director",
        "letter from president",
        "letter from the president",
        
        # Chairman messages
        "chairman's letter",
        "chairmans letter",
        "chairman's message",
        "chairmans message",
        "chairman message",
        "message from chairman",
        "message from the chairman",
        "message from our chairman",
        "message from your chairman",
        
        # CEO messages
        "ceo message",
        "ceo's message",
        "ceos message",
        "message from ceo",
        "message from the ceo",
        "message from our ceo",
        "message from your ceo",
        
        # MD messages
        "md message",
        "md's message",
        "mds message",
        "md and ceo message",
        "md & ceo message",
        "md and ceo's message",
        "md & ceo's message",
        "managing director message",
        "managing director's message",
        "managing directors message",
        "message from md",
        "message from the md",
        "message from managing director",
        "message from the managing director",
        "the md and",  # Incomplete heading pattern
        
        # President/Founder messages  
        "president's message",
        "presidents message",
        "president message",
        "message from president",
        "message from the president",
        "founder's message",
        "founders message",
        "founder message",
        "message from founder",
        "message from the founder",
        
        # Generic messages (common in reports)
        "message from",  # Catches "MESSAGE FROM" and partial patterns
        "message from from",  # Typo pattern found
        "message from the",  # Incomplete pattern
        
        # Dear Shareholder/Stakeholder variations
        "dear stakeholders",
        "dear stakeholder",
        "dear shareholders",
        "dear shareholder",
        "dear shareholder family",
        "dear shareholder,",
        "dear shareholders,",
        "dear stakeholder,",
        "dear stakeholders,",
        
        # Additional greeting variations
        "dear members",
        "dear member",
        "dear investor",
        "dear investors",
        "dear friends",
        "to our shareholders",
        "to our stakeholders",
        "to the shareholders",
        "to the stakeholders",
        "to all stakeholders",
        "towards all stakeholders",
        
        # Joint addressee patterns
        "dear shareholders and stakeholders",
        "dear shareholders & stakeholders",
        "dear members and shareholders",
        
        # Additional chairman/ceo communication styles
        "chairman's statement",
        "chairmans statement",
        "chairman statement",
        "ceo's statement",
        "ceos statement",
        "ceo statement",
        "statement from chairman",
        "statement from ceo",
        "statement from the chairman",
        "statement from the ceo",
        
        # Overview/note patterns (often used for letters)
        "chairman's overview",
        "chairmans overview",
        "ceo's overview",
        "ceos overview",
        "chairman's note",
        "chairmans note",
        "ceo's note",
        "ceos note",
        "note from chairman",
        "note from ceo",
        "note from the chairman",
        "note from the ceo",
        
        # Foreword patterns
        "chairman's foreword",
        "chairmans foreword",
        "ceo's foreword",
        "ceos foreword",
        "foreword by chairman",
        "foreword by ceo",
        "foreword from chairman",
        "foreword from ceo",
        
        # Desk patterns (common in Indian reports)
        "from the chairman's desk",
        "from the chairmans desk",
        "from the ceo's desk",
        "from the ceos desk",
        "from chairman's desk",
        "from chairmans desk",
        "from ceo's desk",
        "from ceos desk",
        "chairman's desk",
        "chairmans desk",
        "ceo's desk",
        "ceos desk",
        "md's desk",
        "mds desk",
        "from the md's desk",
        "from the mds desk"
    ]
}

# Keywords that indicate section end
SECTION_END_KEYWORDS = [
    "financial statements",
    "consolidated financial statements",
    "notes to financial statements",
    "auditor's report",
    "auditors report",
    "independent auditor",
    "balance sheet",
    "income statement",
    "cash flow statement",
    "statement of financial position"
]
