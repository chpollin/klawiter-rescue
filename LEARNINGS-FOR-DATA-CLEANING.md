# Learnings for Data Cleaning: Stefan Zweig Bibliography

## Dataset Overview
- **5,652 entries** with 15 columns from MediaWiki database extraction
- **Source**: 8 BLOBs from Klawiter database (BLOB distribution: BLOB 5: 27.76%, BLOB 4: 23.04%, BLOB 7: 16.76%)
- **Format**: CSV with mixed content types, significant missing data, and encoding issues

## Critical Issues (Prioritized)

### 1. Character Encoding Issues (HIGH)
- **55.52% of entries** affected by Mojibake (incorrectly interpreted UTF-8 as Latin-1)
- **Common patterns**: ä→Ã¤ (20.21%), ü→Ã¼ (22.74%), ö→Ã¶ (9.93%), é→Ã© (13.48%)
- **Examples**: wÃ¤re→wäre, KongreÃŸes→Kongresses, Ã–sterreichische→Österreichische
- **Solution**: Multi-stage character mapping with language-sensitive validation
```python
encoding_fixes = {
    'Ã¤': 'ä', 'Ã¶': 'ö', 'Ã¼': 'ü', 'Ãœ': 'Ü', 'ÃŸ': 'ß', 'Ã©': 'é',
    'Ã¨': 'è', 'Ã²': 'ò', 'Ã¹': 'ù', 'Ã¡': 'á', 'Ãº': 'ú', 'Ã­': 'í',
    'Ã³': 'ó', 'Ã±': 'ñ', 'Ãª': 'ê', 'Ã´': 'ô', 'Ã®': 'î', 'Ã»': 'û',
    'Ã§': 'ç', 'Â°': '°', 'Ã€': 'À', 'ÃŠ': 'Ê', 'Ãˆ': 'È', 'Ã‰': 'É'
}
```

### 2. Content Type Misclassification (HIGH)
- **27.33% redirects misclassified**: 1,545 redirect entries (starting with #REDIRECT) mostly labeled as "Other"
- **Inappropriate categories**: All 8 "Bibliography Entry" items are actually redirects
- **Current distribution**: Category (72.54%), Other (26.47%), specialized types (1%)
- **Solution**: Rule-based reclassification with validation and redirect resolution

### 3. Unstructured Content Field (HIGH)
- **Content field contains mix** of bibliographic details, wiki markup, HTML, URLs, and metadata
- **Needs parsing** to extract: titles, authors, publication details, translators, page numbers, etc.
- **Markup types**: Wiki links (`[[...]]`), HTML tags (`<br/>`, `<div>`), list tags (`<lst>`)
- **Solution**: Pattern-based extraction with targeted parsers for each content type

### 4. Missing Metadata (MEDIUM)
- **page_title**: 100% missing
- **language**: 98.80% missing (needs standardization to ISO codes: 'de', 'en', 'fr', etc.)
- **publisher**: 92.39% missing
- **page_count**: 82.36% missing (needs conversion to numeric)
- **location**: 74.43% missing (needs standardization: "Wien" vs. "Vienna")
- **year**: 31.83% missing (needs clear definition: publication year vs. subject year)
- **Solution**: Pattern-based extraction with confidence scoring and standardization

### 5. Redundant/Unclear Columns (LOW)
- **title_match**: Always False, purpose unclear
- **blob_id**: Internal identifier, possibly not needed for final dataset
- **Solution**: Evaluate and remove non-essential columns

## Content Patterns & Extraction Rules

### Content Types
```
| Type          | Pattern                                  | Confidence |
|---------------|------------------------------------------|------------|
| Redirect      | ^#REDIRECT \[\[(.*?)\]\]                 | 100%       |
| Category      | \[\[Category:(.*?)(?:\|.*?)?\]\]         | 100%       |
| Essay         | \b(essay|essays|aufsatz|aufsätze)\b      | 85%        |
| Translation   | \b(translation|translated by|übersetzt)\b| 90%        |
| Biography     | \b(biography|biographie|life of)\b       | 80%        |
| Collection    | \b(collection|sammlung|collected works)\b| 75%        |
| Review        | \b(review|reviewed|critique|rezension)\b | 90%        |
| Correspondence| \b(letter|brief|correspondence)\b        | 85%        |
| Film/Media    | \b(film|movie|adaptation|recording)\b    | 85%        |
```

### Metadata Extraction
```python
# Title patterns (prioritized)
title_patterns = [
    r"'''(.*?)'''",                                # Triple quotes
    r'^([^#\[\n]{3,100})$',                        # First non-empty line
    r'\[\[([^]|]+)(?:\|[^]]+)?\]\]',               # Wiki links
    r'"([^"]+)"(?:\s+in|\s+\[)',                   # Quoted titles followed by "in" or "["
]

# Year patterns with confidence
year_patterns = [
    (r'(?:published|erschienen|veröffentlicht).*?(\d{4})', 0.9),  # Explicit publication
    (r'\[(\d{4})\]', 0.8),                                         # Year in brackets
    (r'\b(1[8-9]\d{2}|20[0-2]\d)\b', 0.7),                         # Any year in range
]

# Publisher patterns with confidence
publisher_patterns = [
    (r'(?:Verlag|Publisher|Press):\s*([\w\s&\.,\-]+)', 0.9),
    (r'(?:published by|verlegt bei)\s*([\w\s&\.,\-]+)', 0.9),
    (r'\b(?:Verlag|Publishers?)\b[^\n.]*?([\w\s&\.,\-]+)(?:,|\.|$)', 0.8),
]

# Location normalization mapping
location_map = {
    'Wien': 'Vienna', 'Zürich': 'Zurich', 'München': 'Munich', 
    'Köln': 'Cologne', 'Praha': 'Prague', 'Moskva': 'Moscow'
}

# Language detection and standardization
def detect_language(text):
    # ISO language code determination
    lang_indicators = {
        'de': ['verlag', 'deutsche', 'herausgegeben', 'übersetzt'],
        'en': ['publisher', 'english', 'translated', 'edited by'],
        'fr': ['édition', 'française', 'traduit', 'publié'],
        'es': ['edición', 'española', 'traducido', 'publicado'],
        'it': ['edizione', 'italiana', 'tradotto', 'pubblicato']
    }
    # Implement detection logic with scoring
```

### HTML/Wiki Markup Processing
```python
def clean_markup(text):
    """Remove markup while preserving semantic information"""
    # Remove HTML tags but preserve content
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<div[^>]*>(.*?)</div>', r'\1', text, flags=re.DOTALL)
    
    # Convert wiki links to plain text
    text = re.sub(r'\[\[([^]|]+)\|([^]]+)\]\]', r'\2', text)  # [[link|text]] -> text
    text = re.sub(r'\[\[([^]|]+)\]\]', r'\1', text)            # [[link]] -> link
    
    # Handle list tags
    text = re.sub(r'<lst[^>]*>(.*?)</lst>', r'\1', text, flags=re.DOTALL)
    
    # Remove category tags
    text = re.sub(r'\[\[Category:.*?\]\]', '', text)
    
    return text.strip()
```

### URL Validation and Extraction
```python
def extract_urls(text):
    """Extract and validate URLs from text"""
    url_pattern = r'https?://[\w\-\.]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
    urls = re.findall(url_pattern, text)
    
    valid_urls = []
    for url in urls:
        # Basic validation
        if url.startswith(('http://', 'https://')) and '.' in url:
            valid_urls.append(url)
    
    return valid_urls
```