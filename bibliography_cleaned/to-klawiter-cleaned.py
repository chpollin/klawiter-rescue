import pandas as pd
import re
import logging
import os
from datetime import datetime
import unicodedata
import codecs

# Set up logging
log_filename = f"zweig_cleaning_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def log_dataframe_info(df, description):
    """Log information about the dataframe"""
    logger.info(f"\n{description}:")
    logger.info(f"Shape: {df.shape}")
    logger.info(f"Columns: {df.columns.tolist()}")
    logger.info(f"Data types:\n{df.dtypes}")
    logger.info(f"Missing values:\n{df.isna().sum()}")
    logger.info(f"First 5 rows:\n{df.head().to_string()}")

def fix_encoding(text):
    """Fix character encoding issues in text with improved support for various scripts"""
    if pd.isna(text):
        return text
    
    # Handle potential bytes string
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = text.decode('latin1')
            except UnicodeDecodeError:
                logger.warning(f"Failed to decode bytes: {text[:50]}...")
                return str(text)
    
    # Normalize Unicode to handle different normalization forms
    text = unicodedata.normalize('NFC', text)
    
    # Fix Cyrillic transliteration
    text = re.sub(r'(?<!\\)Ä­', 'ĭ', text)  # Fix ĭ (short i with breve) for Cyrillic
    text = re.sub(r'(?<!\\)iā­', 'iĭ', text)  # Fix common pattern in Russian names
    text = re.sub(r'(?<!\\)eā­n', 'eĭn', text)  # Fix Bernshteĭn
    text = re.sub(r'(?<!\\)shteā­', 'shteĭ', text)  # Fix Bernshteĭn
    text = re.sub(r'(?<!\\)skiā­', 'skiĭ', text)  # Fix Arskiĭ
    text = re.sub(r'(?<!\\)skiā­\.', 'skiĭ.', text)  # With period
    
    # Fix Indic transliteration (enhanced for Hindi/Sanskrit)
    # Fix common virama issues
    text = re.sub(r'(?<!\\)viá¸', 'viḍ', text)  # Fix viḍ (d with dot below)
    text = re.sub(r'(?<!\\)á¸am', 'ḍam', text)  # Fix ḍam
    text = re.sub(r'(?<!\\)á¹‡a', 'ṇa', text)  # Fix ṇa (n with dot below)
    text = re.sub(r'(?<!\\)á¹£', 'ṣ', text)  # Fix ṣ (s with dot below)
    text = re.sub(r'(?<!\\)á¸¥', 'ḥ', text)  # Fix ḥ (h with dot below)
    text = re.sub(r'(?<!\\)á¹­', 'ṭ', text)  # Fix ṭ (t with dot below)
    text = re.sub(r'(?<!\\)á¹ƒ', 'ṃ', text)  # Fix ṃ (m with dot below)
    
    # Fix for Hindi titles
    text = re.sub(r'(?<!\\)Bhč', 'Bhā', text)  # Fix Bhā (long a)
    text = re.sub(r'(?<!\\)č(?=[a-zA-Z])', 'ā', text)  # Fix ā (long a) when followed by letter
    text = re.sub(r'(?<!\\)ī(?=[a-zA-Z])', 'ī', text)  # Fix ī (long i)
    text = re.sub(r'(?<!\\)ū(?=[a-zA-Z])', 'ū', text)  # Fix ū (long u)
    text = re.sub(r'(?<!\\)Mč', 'Mā', text)  # Fix Mā in names
    text = re.sub(r'(?<!\\)(?<=[a-zA-Z])č', 'ā', text)  # Fix ā when preceded by letter
    
    # Fix specific Indic patterns
    text = re.sub(r'(?<!\\)upanyčso', 'upanyāso', text)  # Fix upanyāso
    text = re.sub(r'(?<!\\)rūpčntar', 'rūpāntar', text)  # Fix rūpāntar
    text = re.sub(r'(?<!\\)hindī', 'hindī', text)  # Fix hindī
    text = re.sub(r'(?<!\\)istuvčrt', 'istuvārt', text)  # Fix istuvārt (Stuart)
    
    # Fix Arabic transliteration
    text = re.sub(r'(?<!\\)Ä€', 'Ā', text)
    text = re.sub(r'(?<!\\)Ä«', 'ī', text)
    text = re.sub(r'(?<!\\)Å«', 'ū', text)
    
    # Advanced Arabic transliteration fixes
    text = re.sub(r'(?<!\\)DÄr', 'Dār', text)
    text = re.sub(r'(?<!\\)MadÄ', 'Madā', text)
    text = re.sub(r'(?<!\\)ThaqÄfah', 'Thaqāfah', text)
    text = re.sub(r'(?<!\\)BaghdÄd', 'Baghdād', text)
    text = re.sub(r'(?<!\\)ÄshiqÄt', 'Āshiqāt', text)
    text = re.sub(r'(?<!\\)"\'Ālam', "'Ālam", text)
    text = re.sub(r'(?<!\\)waÊ¾l', "wa'l", text)  # Arabic ain character with connecting letter
    
    # Fix German and other European language characters
    text = re.sub(r'(?<!\\)Ã¤', 'ä', text)
    text = re.sub(r'(?<!\\)Ã¶', 'ö', text)
    text = re.sub(r'(?<!\\)Ã¼', 'ü', text)
    text = re.sub(r'(?<!\\)ÃŸ', 'ß', text)
    text = re.sub(r'(?<!\\)Ã„', 'Ä', text)
    text = re.sub(r'(?<!\\)Ã–', 'Ö', text)
    text = re.sub(r'(?<!\\)Ãœ', 'Ü', text)
    
    # Fix common German problematic cases
    text = re.sub(r'(?<!\\)w re ', 'wäre ', text)  # Fix common "wäre" issue
    text = re.sub(r'(?<!\\)kongre ', 'kongre', text)  # Part of Antikriegskongreßes
    text = re.sub(r'(?<!\\)gre es', 'greßes', text)  # Part of Antikriegskongreßes
    
    # Fix Spanish and other Latin character issues
    text = re.sub(r'(?<!\\)Ã¡', 'á', text)
    text = re.sub(r'(?<!\\)Ã©', 'é', text)
    text = re.sub(r'(?<!\\)Ã­', 'í', text)
    text = re.sub(r'(?<!\\)Ã³', 'ó', text)
    text = re.sub(r'(?<!\\)Ãº', 'ú', text)
    text = re.sub(r'(?<!\\)Ã±', 'ñ', text)
    
    # Fix Portuguese/French specific characters
    text = re.sub(r'(?<!\\)Ã£', 'ã', text)  # a with tilde
    text = re.sub(r'(?<!\\)Ãµ', 'õ', text)  # o with tilde
    text = re.sub(r'(?<!\\)Ã¢', 'â', text)  # a with circumflex
    text = re.sub(r'(?<!\\)Ãª', 'ê', text)  # e with circumflex
    text = re.sub(r'(?<!\\)Ã®', 'î', text)  # i with circumflex
    text = re.sub(r'(?<!\\)Ã´', 'ô', text)  # o with circumflex
    text = re.sub(r'(?<!\\)Ã»', 'û', text)  # u with circumflex
    text = re.sub(r'(?<!\\)Ã§', 'ç', text)  # c cedilla
    
    # Fix Eastern European characters
    text = re.sub(r'(?<!\\)Å¡', 'š', text)  # s caron (Czech/Slovak/Slovenian/Croatian)
    text = re.sub(r'(?<!\\)Å½', 'Ž', text)  # Z caron
    text = re.sub(r'(?<!\\)Å¾', 'ž', text)  # z caron
    text = re.sub(r'(?<!\\)Ä', 'č', text)  # c caron
    text = re.sub(r'(?<!\\)Å™', 'ř', text)  # r caron (Czech)
    text = re.sub(r'(?<!\\)Å„', 'ń', text)  # n acute (Polish)
    text = re.sub(r'(?<!\\)Å‚', 'ł', text)  # l with stroke (Polish)
    
    # Fix Cyrillic characters
    text = re.sub(r'(?<!\\)Ä­', 'ĭ', text)  # Cyrillic short i (as in Arskiĭ)
    text = re.sub(r'(?<!\\)Ð', 'И', text)  # Cyrillic I
    text = re.sub(r'(?<!\\)Ñ', 'Н', text)  # Cyrillic N
    
    # Fix ligatures and special typography
    text = re.sub(r'(?<!\\)Å"', 'œ', text)  # oe ligature
    text = re.sub(r'(?<!\\)Ã¦', 'æ', text)  # ae ligature
    text = re.sub(r'(?<!\\)Å¸', 'ÿ', text)  # y with diaeresis
    
    # Fix HTML/XML entities
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&mdash;', '—', text)
    text = re.sub(r'&ndash;', '–', text)
    text = re.sub(r'&lsquo;', ''', text)
    text = re.sub(r'&rsquo;', ''', text)
    text = re.sub(r'&ldquo;', '"', text)
    text = re.sub(r'&rdquo;', '"', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    
    # Fix numeric character references
    text = re.sub(r'&#8211;', '–', text)  # en dash
    text = re.sub(r'&#8212;', '—', text)  # em dash
    text = re.sub(r'&#8216;', ''', text)  # left single quote
    text = re.sub(r'&#8217;', ''', text)  # right single quote
    text = re.sub(r'&#8220;', '"', text)  # left double quote
    text = re.sub(r'&#8221;', '"', text)  # right double quote
    
    # Fix smart quotes and similar characters
    text = re.sub(r'(?<!\\)â€™', "'", text)  # right single quote
    text = re.sub(r'(?<!\\)â€œ', '"', text)  # left double quote
    text = re.sub(r'(?<!\\)â€', '"', text)   # right double quote
    text = re.sub(r'(?<!\\)â€"', '-', text)  # en dash
    text = re.sub(r'(?<!\\)â€"', '—', text)  # em dash
    text = re.sub(r'(?<!\\)â€¦', '…', text)  # ellipsis
    
    # Fix common mojibake patterns for various scripts
    text = re.sub(r'(?<!\\)SadhÃ¢na', 'Sadhâna', text)  # Sanskrit/Hindi term
    
    # Fix specific known patterns from the examples
    text = re.sub(r'\\\'\Ālam', "'Ālam", text)  # Fix escaped quote with Arabic
    text = re.sub(r"fī \\'l", "fī 'l", text)    # Fix escaped quote with Arabic
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Fix double-encoded characters (characters encoded twice)
    text = re.sub(r'(?<!\\)Ã£Â£', 'ã', text)
    text = re.sub(r'(?<!\\)Ã£Â¢', 'â', text)
    
    # Remove zero-width spaces and other invisible characters
    text = re.sub(r'\u200B', '', text)  # zero-width space
    text = re.sub(r'\u200C', '', text)  # zero-width non-joiner
    text = re.sub(r'\u200D', '', text)  # zero-width joiner
    text = re.sub(r'\u2060', '', text)  # word joiner
    text = re.sub(r'\uFEFF', '', text)  # byte order mark
    
    # Additional cleanup for titles with quotes
    text = re.sub(r'\\+"', '"', text)  # Remove escaped quotes
    text = re.sub(r'\\+"', '"', text)  # Sometimes double escaping
    
    # Fix doubled quotes in strings (common in CSV processing)
    text = re.sub(r'(?<!\\)""', '"', text)  # Double quotes to single quotes
    
    return text

def fix_encoding_deep(text):
    """Apply multiple passes of encoding fixes for complex cases"""
    if pd.isna(text):
        return text
    
    # Try different encoding schemes for particularly difficult cases
    try:
        # First attempt normal fix
        fixed_text = fix_encoding(text)
        
        # If we still detect encoding issues, try more aggressive approaches
        if re.search(r'[Ã|Ä|Å|á¸|á¹|č|ā­]', fixed_text):
            # Try to decode as latin1, then utf-8
            try:
                bytes_text = fixed_text.encode('latin1')
                decoded = bytes_text.decode('utf-8')
                fixed_text = fix_encoding(decoded)
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
            
            # Try another pass of fixing
            fixed_text = fix_encoding(fixed_text)
        
        return fixed_text
    except Exception as e:
        logger.warning(f"Error in deep encoding fix: {str(e)}")
        return text

def remove_wiki_markup(text):
    """Remove wiki markup from text completely"""
    if pd.isna(text):
        return ""
    
    # Remove category tags
    text = re.sub(r'\[\[Category:.*?\]\]', '', text)
    
    # Remove DEFAULTSORTKEY tags
    text = re.sub(r'\{\{DEFAULTSORTKEY:.*?\}\}', '', text)
    
    # Replace [[Link|Text]] with just Text
    text = re.sub(r'\[\[(.*?\|)?(.*?)\]\]', r'\2', text)
    
    # Replace <lst...> tags with their content
    text = re.sub(r'<lst.*?>(.*?)</lst>', r'\1', text, flags=re.DOTALL)
    
    # Remove '''text''' (bold)
    text = re.sub(r"'''(.*?)'''", r'\1', text)
    
    # Remove ''text'' (italic)
    text = re.sub(r"''(.*?)''", r'\1', text)
    
    # Remove #REDIRECT
    text = re.sub(r'#REDIRECT \[\[(.*?)\]\]', r'\1', text)
    text = re.sub(r'#REDIRECT ', '', text)
    
    # Remove escaped quotes
    text = re.sub(r'\\"', '"', text)
    text = re.sub(r"\\'", "'", text)
    
    # Clean up newlines and extra spaces - replace with spaces
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Final cleanup
    return text.strip()

def extract_categories(text):
    """Extract categories from wiki markup"""
    if pd.isna(text):
        return []
    categories = re.findall(r'\[\[Category:(.*?)\]\]', text)
    return categories

def extract_redirect_target(text):
    """Extract clean redirect target without markup"""
    if pd.isna(text):
        return None
    if not text.startswith('#REDIRECT'):
        return None
    
    # Extract content between [[ and ]]
    match = re.search(r'#REDIRECT \[\[(.*?)\]\]', text)
    if match:
        return match.group(1)
    return None

def get_main_category(categories):
    """Get main category classification based on first segment before '/'"""
    if not categories:
        return ""
    
    # Take the first category and split by '/'
    main_cat = categories[0].split('/')[0].strip()
    return main_cat

def assign_time_period(year):
    """Assign a time period based on the publication year"""
    if pd.isna(year):
        return ""
    
    try:
        year = float(year)
        
        if year < 1881:
            return "Pre-Zweig (before 1881)"
        elif 1881 <= year <= 1942:
            return "During Lifetime (1881-1942)"
        elif 1942 < year <= 1980:
            return "Post-WWII (1943-1980)"
        elif 1980 < year <= 2000:
            return "Late 20th Century (1981-2000)"
        elif year > 2000:
            return "Contemporary (after 2000)"
        else:
            return ""
    except (ValueError, TypeError):
        return ""

def extract_transliterated_title_and_original(content):
    """Extract both transliterated title and original title from content,
    handling cases where the title is in a different script than the original"""
    if pd.isna(content):
        return "", ""
    
    # Clean the content of unnecessary markup for easier processing
    clean_content = remove_wiki_markup(content)
    
    # First check for transliterated titles in the Contents section
    contents_pattern = re.search(r'Contents\s*\n(.*?)(?:\n\n|\Z)', clean_content, re.DOTALL | re.IGNORECASE)
    
    if contents_pattern:
        contents_text = contents_pattern.group(1)
        # Look for content items with format: "Russian title [German title]"
        content_items = re.findall(r'([^[\n]+)\s*\[(.*?)(?:\.\s*Translated|\])', contents_text)
        
        
        if content_items and len(content_items) >= 2:
            # For collections with multiple works, create a combined title
            # Use the first two content items as the main components of the title
            main_titles = []
            original_titles = []
            
            for i, (trans_title, orig_title) in enumerate(content_items[:2]):
                if trans_title.strip():
                    main_titles.append(trans_title.strip())
                    if orig_title.strip():
                        # Clean up original title by removing trailing characters
                        clean_orig = re.sub(r'\.\s*Translated.*$', '', orig_title).strip()
                        original_titles.append(clean_orig)
            
            if main_titles:
                return " * ".join(main_titles), " * ".join(original_titles)
    
    # Pattern for detecting content with original title in brackets after the title
    title_with_original_pattern = re.search(r'^([^[]+)\s*\[(.*?)\]', clean_content)
    
    if title_with_original_pattern:
        transliterated_title = title_with_original_pattern.group(1).strip()
        original_title = title_with_original_pattern.group(2).strip()
        return transliterated_title, original_title
    
    # Check for bracketed content at the beginning which might be the original title
    bracket_at_start = re.match(r'^\s*\[(.*?)\]', clean_content)
    if bracket_at_start:
        original_title = bracket_at_start.group(1)
        
        # Look for content items in the text to find the transliterated title
        contents_anywhere = re.search(r'Contents.*?\n(.*?)(?:\n\n|\Z)', clean_content, re.DOTALL | re.IGNORECASE)
        if contents_anywhere:
            content_text = contents_anywhere.group(1)
            item_matches = re.findall(r'([^[\n]+)\s*\[', content_text)
            if item_matches and len(item_matches) >= 2:
                # Create combined title from first two content items
                combined_title = " * ".join([item.strip() for item in item_matches[:2]])
                return combined_title, original_title
    
    # Default fall back to simpler extraction
    bracket_match = re.search(r'\[(.*?)\]', clean_content)
    if bracket_match:
        return "", bracket_match.group(1)
    
    # Most basic extraction
    if '.' in clean_content:
        parts = re.split(r'(?<!\w)\.(?!\w)', clean_content)
        title_candidate = parts[0].strip()
        return title_candidate, ""
    else:
        return clean_content.strip(), ""

def extract_title(row):
    """Extract and clean a title from the content, with improved handling of translated works"""
    # First try to use redirect for redirect entries
    if not pd.isna(row.get('redirect')):
        title = row['redirect']
        title = remove_wiki_markup(title)
        return title
    
    # For Bibliography or translation entries, try the enhanced extraction logic
    transliterated_title, original_title = extract_transliterated_title_and_original(row.get('content_cleaned', ''))
    
    # If we have both titles, prioritize the transliterated one as the main title
    if transliterated_title:
        return transliterated_title
    
    # If we only have an original title, use that
    if original_title:
        return original_title
    
    # Fall back to the old method
    content = row.get('content_cleaned', '')
    if pd.isna(content):
        return ""
    
    # Extract the first sentence or up to first period for a title
    content = remove_wiki_markup(content)
    
    if '.' in content:
        parts = re.split(r'(?<!\w)\.(?!\w)', content)
        title_candidate = parts[0].strip()
    else:
        title_candidate = content.strip()
    
    # If title is too long, truncate it
    if len(title_candidate) > 100:
        words = title_candidate.split()
        title_candidate = ' '.join(words[:10]) + "..."
    
    return title_candidate

def format_categories(categories_list):
    """Format categories list into a readable string"""
    if not categories_list:
        return ""
    
    # Clean up any extra spaces in category names
    cleaned_categories = []
    for cat in categories_list:
        # Normalize spaces
        cat = re.sub(r'\s+', ' ', cat.strip())
        cleaned_categories.append(cat)
    
    return '; '.join(cleaned_categories)

def extract_catalog_numbers(text_id):
    """Extract catalog numbers from text_id field if available"""
    if pd.isna(text_id):
        return "", ""
    
    # Check if text_id contains comma-separated values
    parts = str(text_id).split(',')
    if len(parts) >= 2:
        return parts[0], parts[1]
    else:
        return "", ""  # Return empty strings if no comma-separated values

def extract_original_title(content, transliterated_title=None):
    """Extract original title from content if available,
    with improved handling of bracketed original titles"""
    if pd.isna(content):
        return ""
    
    # If we already computed the transliterated title, use it for context
    if transliterated_title:
        # Use the transliterated title to help find the original title
        clean_content = remove_wiki_markup(content)
        after_title = clean_content
        if transliterated_title in clean_content:
            after_title_idx = clean_content.find(transliterated_title) + len(transliterated_title)
            after_title = clean_content[after_title_idx:].strip()
        
        # Look for bracketed text immediately after the transliterated title
        bracket_match = re.search(r'^\s*\[(.*?)\]', after_title)
        if bracket_match:
            return bracket_match.group(1)
    
    # If we don't have a transliterated title or couldn't find a match,
    # try the standard approach of looking for bracketed text
    # Look for titles in square brackets which often indicate original titles
    bracket_match = re.search(r'\[(.*?)\]', content)
    if bracket_match:
        original_title = bracket_match.group(1)
        # Remove any leftover brackets
        original_title = re.sub(r'^\[|\]$', '', original_title)
        return original_title
    
    return ""

def extract_full_bibliographic_entry(content):
    """Extract full bibliographic entry from content"""
    if pd.isna(content):
        return ""
    
    # For bibliography entries, the first paragraph usually contains the full entry
    # Remove wiki markup first
    clean_content = remove_wiki_markup(content)
    
    # Get the first paragraph or up to 250 characters
    if '\n\n' in clean_content:
        entry = clean_content.split('\n\n')[0]
    else:
        entry = clean_content[:min(250, len(clean_content))]
        
    return entry.strip()

def extract_content_items(content):
    """Extract content items (chapters, sections, contributions) from the bibliography entry
    with improved handling of lists and tables of contents"""
    if pd.isna(content):
        return {}, {}, {}, {}
    
    # Clean the content
    clean_content = remove_wiki_markup(content)
    
    # Look for "Contents" section with multiple pattern matching strategies
    contents_section = None
    
    # 1. Try standard "Contents" header
    contents_match = re.search(r'[Cc]ontents\s*\n(.*?)(?:\n\n|\Z)', clean_content, re.DOTALL)
    if contents_match:
        contents_section = contents_match.group(1)
    
    # 2. Try numbered content items directly
    if not contents_section:
        numbered_items_match = re.search(r'(?:\n\n|\n)(\d+\.\s+.*?)(?:\n\n|\Z)', clean_content, re.DOTALL)
        if numbered_items_match:
            contents_section = numbered_items_match.group(1)
    
    # 3. Look for patterns like "1. Title [Original]" even without a Contents header
    if not contents_section:
        item_list_match = re.findall(r'(?:\n|^)(\d+\.\s+.*?)(?:\n\d+\.|\Z)', clean_content, re.DOTALL)
        if item_list_match:
            contents_section = '\n'.join(item_list_match)
    
    # 4. Try entries with a line break format
    if not contents_section:
        item_list_match = re.findall(r'(?:\n|^)([^.\n]+)\s*\[.*?\].*?(?:\n|$)', clean_content)
        if item_list_match and len(item_list_match) > 1:  # At least 2 items to consider it a contents list
            contents_section = '\n'.join(item_list_match)
    
    content_items = {}
    content_original_titles = {}
    content_translators = {}
    content_pages = {}
    
    if contents_section:
        # Split by numbered items or line breaks
        items = re.split(r'\n\d+\.|\n-|\n\*|\n', contents_section)
        items = [item.strip() for item in items if item.strip()]
        
        for i, item in enumerate(items, 1):
            # Extract translated title, original title, translator, and pages
            
            # Look for pages in format "pp. X-Y"
            pages_match = re.search(r'pp\.\s*(\(?\d+\)?-\d+|\d+)', item)
            pages = pages_match.group(1) if pages_match else ""
            
            # Look for original title in square brackets
            original_title_match = re.search(r'\[(.*?)\]', item)
            original_title = original_title_match.group(1) if original_title_match else ""
            
            # Look for translator info - expanded patterns
            translator_match = re.search(r'(?:[Tt]ranslated by|[Tt]r\.)\s+(.*?)[\.,]', item)
            if not translator_match:
                translator_match = re.search(r'(?:[Tt]ranslation by|[Tt]rans\.)\s+(.*?)[\.,]', item)
            translator = translator_match.group(1) if translator_match else ""
            
            # Clean up the title by removing the parts we've extracted
            title = item
            if original_title:
                title = re.sub(r'\[.*?\]', '', title)
            if translator:
                title = re.sub(r'(?:[Tt]ranslated by|[Tt]r\.|[Tt]ranslation by|[Tt]rans\.)\s+.*?[\.,]', '', title)
            if pages:
                title = re.sub(r'pp\.\s*\(?\d+\)?-\d+|\d+', '', title)
            
            # Clean up any remaining punctuation and whitespace
            title = re.sub(r'[,\.:;]+\s*$', '', title.strip())
            
            content_items[f"content_item_{i}_title"] = title.strip()
            content_original_titles[f"content_item_{i}_original_title"] = original_title.strip()
            content_translators[f"content_item_{i}_translator"] = translator.strip()
            content_pages[f"content_item_{i}_pages"] = pages.strip()
    
    return content_items, content_original_titles, content_translators, content_pages

def extract_publisher_location_info(content):
    """Extract publisher and location information from bibliographic entry"""
    if pd.isna(content):
        return "", ""
    
    clean_content = remove_wiki_markup(content)
    
    # Look for common patterns in bibliographic entries
    # Publisher pattern: "Publisher Name, Year" or "City: Publisher Name, Year"
    publisher_match = re.search(r'(?:[A-Z][a-zA-Z\s]+:)?\s*([^,]+?)(?:,|\s+\d{4})', clean_content)
    publisher = publisher_match.group(1).strip() if publisher_match else ""
    
    # Better pattern for finding publishers in complex entries
    advanced_publisher_match = re.search(r'(?:Izdatel\'stvo|Publishing|Verlag|Éditions)\s+"?([^",.]+)"?', clean_content)
    if advanced_publisher_match:
        publisher = advanced_publisher_match.group(1).strip()
    
    # Also look for publisher patterns with quotes
    quoted_publisher_match = re.search(r':\s+"([^"]+)"', clean_content)
    if quoted_publisher_match:
        publisher = quoted_publisher_match.group(1).strip()
    
    # Try to extract a location
    location_match = re.search(r'([A-Z][a-zA-Z\s]+):', clean_content)
    location = location_match.group(1).strip() if location_match else ""
    
    # Look for common city names that might not be followed by a colon
    city_pattern = r'(?:^|\s)(Moscow|Moskva|Berlin|London|New York|Paris|Wien|Vienna|Frankfurt|Leipzig)\b'
    city_match = re.search(city_pattern, clean_content, re.IGNORECASE)
    if city_match and not location:
        location = city_match.group(1).strip()
    
    return publisher, location

def extract_language_from_categories(categories):
    """Extract language information from categories"""
    if not categories:
        return ""
    
    language_map = {
        "Russian": "Russian",
        "German": "German",
        "English": "English",
        "French": "French",
        "Spanish": "Spanish",
        "Italian": "Italian",
        "Portuguese": "Portuguese",
        "Japanese": "Japanese",
        "Chinese": "Chinese",
        "Arabic": "Arabic",
        "Hindi": "Hindi",
        "Sanskrit": "Sanskrit",
        "Hebrew": "Hebrew"
    }
    
    for cat in categories:
        for lang, lang_name in language_map.items():
            if lang in cat:
                return lang_name
    
    return ""

def extract_page_count(content):
    """Extract page count from bibliographic entry"""
    if pd.isna(content):
        return ""
    
    clean_content = remove_wiki_markup(content)
    
    # Look for page count in format "XXXp." or "XXX pages" or "p. XXX"
    page_count_match = re.search(r'(\d+)\s*(?:p\.|pages)', clean_content)
    if page_count_match:
        return page_count_match.group(1)
    
    # Another pattern: "XXX/(Y)p." common in the dataset
    page_count_alt_match = re.search(r'(\d+)/\(\d+\)p\.', clean_content)
    if page_count_alt_match:
        return page_count_alt_match.group(1)
    
    # Look for total page numbers mentioned in context
    total_pages_match = re.search(r'(?:total|in all|altogether)\s+(\d+)\s*(?:p\.|pages)', clean_content, re.IGNORECASE)
    if total_pages_match:
        return total_pages_match.group(1)
    
    return ""
    
    # Look for a typical wiki last edited date format
    date_match = re.search(r'This page was last edited on (\d+ [A-Za-z]+ \d{4})', content)
    if date_match:
        return date_match.group(1)
    
    return ""

def clean_zweig_bibliography(input_file, output_file):
    """Main function to clean the Zweig bibliography dataset with enhanced extraction"""
    logger.info(f"Starting enhanced cleaning process for file: {input_file}")
    
    # 1. Data Loading and Initial Assessment
    logger.info("Step 1: Loading data and initial assessment")
    try:
        df = pd.read_csv(input_file)
    except UnicodeDecodeError:
        logger.info("UTF-8 decode error, trying with latin1 encoding")
        df = pd.read_csv(input_file, encoding='latin1')
    except Exception as e:
        logger.error(f"Error loading file: {str(e)}")
        raise
        
    log_dataframe_info(df, "Initial dataset")
    
    # 2. Structural Cleaning
    logger.info("Step 2: Structural cleaning")
    
    # Remove unnecessary columns
    if 'page_title' in df.columns and df['page_title'].isna().all():
        logger.info("Removing 'page_title' column as it's 100% NULL")
        df = df.drop(columns=['page_title'])
    
    # Fix data types if needed
    if 'year' in df.columns:
        logger.info("Converting 'year' column to float type")
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
    
    log_dataframe_info(df, "After structural cleaning")
    
    # 3. Content Normalization
    logger.info("Step 3: Content normalization")
    
    # Fix character encoding in text fields with deep fix for complex cases
    text_columns = ['content', 'content_cleaned', 'redirect_target', 'content_title']
    text_columns = [col for col in text_columns if col in df.columns]
    
    for col in text_columns:
        logger.info(f"Fixing character encoding in '{col}' column")
        df[col] = df[col].apply(fix_encoding_deep)
    
    # Create a clean redirect column
    logger.info("Creating clean redirect column")
    df['redirect'] = df['content'].apply(extract_redirect_target)
    
    # 4. Metadata Enhancement
    logger.info("Step 4: Metadata enhancement")
    
    # Extract categories
    logger.info("Extracting categories from content")
    df['categories_list'] = df['content'].apply(extract_categories)
    
    # Format categories as readable text
    logger.info("Formatting categories as readable text")
    df['categories'] = df['categories_list'].apply(format_categories)
    
    # Add main category classification
    logger.info("Adding main category classification")
    df['main_category'] = df['categories_list'].apply(get_main_category)
    
    # Add time period classification
    logger.info("Adding time period classification")
    df['time_period'] = df['year'].apply(assign_time_period)
    
    # 5. Enhanced metadata extraction
    logger.info("Step 5: Enhanced metadata extraction")
    
    # Extract catalog numbers only if they're different from text_id
    logger.info("Extracting catalog numbers")
    catalog_numbers = df.apply(
        lambda row: pd.Series(extract_catalog_numbers(row.get('text_id', ''))), 
        axis=1
    )
    
    # Only add catalog numbers columns if they provide new information
    if not catalog_numbers.empty and (catalog_numbers.iloc[:, 0].astype(str) != "").any():
        df['catalog_number_1'] = catalog_numbers.iloc[:, 0]
        df['catalog_number_2'] = catalog_numbers.iloc[:, 1]
    else:
        # Skip creating redundant catalog number columns
        logger.info("Skipping catalog number extraction as they match text_id")
    
    # First extract transliterated and original titles together for context
    logger.info("Extracting transliterated and original titles")
    titles_extracted = df.apply(
        lambda row: pd.Series(extract_transliterated_title_and_original(row.get('content_cleaned', ''))),
        axis=1
    )
    
    # If we have extracted titles successfully, use them
    if not titles_extracted.empty:
        df['transliterated_title'] = titles_extracted.iloc[:, 0]
        df['original_title'] = titles_extracted.iloc[:, 1]
        
        # For entries without a clear transliterated title but with an original title,
        # try to extract the original title with the improved method
        mask = (df['transliterated_title'] == "") & (df['original_title'] == "")
        if mask.any():
            df.loc[mask, 'original_title'] = df.loc[mask, 'content'].apply(extract_original_title)
        
        # Clean up original title by removing leftover brackets
        df['original_title'] = df['original_title'].apply(lambda x: re.sub(r'^\[|\]$', '', x) if isinstance(x, str) else x)
    else:
        # If the extraction failed, fall back to the original method
        logger.info("Falling back to original title extraction method")
        df['original_title'] = df['content'].apply(extract_original_title)
        # Clean up original title by removing leftover brackets
        df['original_title'] = df['original_title'].apply(lambda x: re.sub(r'^\[|\]$', '', x) if isinstance(x, str) else x)
    
    # Extract full bibliographic entry
    logger.info("Extracting full bibliographic entry")
    df['full_bibliographic_entry'] = df['content'].apply(extract_full_bibliographic_entry)
    
    # Extract publisher and location information
    logger.info("Extracting publisher and location information")
    publisher_location = df.apply(
        lambda row: pd.Series(extract_publisher_location_info(row.get('content', ''))),
        axis=1
    )
    
    df['publisher_extracted'] = publisher_location.iloc[:, 0]
    df['location_extracted'] = publisher_location.iloc[:, 1]
    
    # Use extracted publisher/location if existing fields are empty
    if 'publisher' not in df.columns:
        df['publisher'] = df['publisher_extracted']
    else:
        df['publisher'] = df.apply(
            lambda row: row['publisher'] if pd.notna(row['publisher']) and row['publisher'] else row['publisher_extracted'],
            axis=1
        )
        
    if 'location' not in df.columns:
        df['location'] = df['location_extracted']
    else:
        df['location'] = df.apply(
            lambda row: row['location'] if pd.notna(row['location']) and row['location'] else row['location_extracted'],
            axis=1
        )
    
    # Extract language information
    logger.info("Extracting language information")
    if 'language' not in df.columns:
        df['language'] = df['categories_list'].apply(extract_language_from_categories)
    elif df['language'].isna().sum() > 0:
        # Fill in missing language values where possible
        extracted_languages = df['categories_list'].apply(extract_language_from_categories)
        df['language'] = df.apply(
            lambda row: row['language'] if pd.notna(row['language']) and row['language'] else extracted_languages.loc[row.name],
            axis=1
        )
    
    # Extract page count
    logger.info("Extracting page count")
    if 'page_count' not in df.columns:
        df['page_count'] = df['content'].apply(extract_page_count)
    elif df['page_count'].isna().sum() > 0:
        # Fill in missing page count values where possible
        extracted_page_counts = df['content'].apply(extract_page_count)
        df['page_count'] = df.apply(
            lambda row: row['page_count'] if pd.notna(row['page_count']) else extracted_page_counts.loc[row.name],
            axis=1
        )
    
    # 6. Extract content items
    logger.info("Step 6: Extracting content items")
    
    # Extract content items, original titles, translators, and page ranges
    content_items_data = df.apply(
        lambda row: pd.Series(extract_content_items(row.get('content', ''))), 
        axis=1
    )
    
    # If there are content items extracted, add them to the dataframe
    if not content_items_data.empty and len(content_items_data.columns) > 0:
        # Add all content item columns to the main dataframe
        for col in content_items_data.columns:
            df[col] = content_items_data[col]
    
    # Now extract titles with access to content items data
    logger.info("Extracting transliterated and original titles")
    titles_extracted = df.apply(
        lambda row: pd.Series(extract_transliterated_title_and_original(row.get('content', ''))),
        axis=1
    )

    # 7. Create fully cleaned content and titles
    logger.info("Step 7: Creating fully cleaned content")
    
    # Create a clean title field with priority to transliterated titles for bilingual works
    logger.info("Creating clean title field")
    if 'transliterated_title' in df.columns:
        # Use transliterated title as primary when available
        df['title'] = df.apply(
            lambda row: row['transliterated_title'] if row['transliterated_title'] else 
                       (extract_title(row) if 'transliterated_title' not in row or not row['transliterated_title'] else ""),
            axis=1
        )
    else:
        df['title'] = df.apply(extract_title, axis=1)
    
    # Clean content - completely remove wiki markup
    logger.info("Completely removing wiki markup from content")
    df['clean_content'] = df['content_cleaned'].apply(remove_wiki_markup)
    
    # Fix any remaining encoding issues in the clean content
    df['clean_content'] = df['clean_content'].apply(fix_encoding_deep)
    
    # 8. Prepare final dataset for manual editing
    logger.info("Step 8: Preparing final dataset for manual editing")
    
    # Define comprehensive columns structure for the final dataset
    # Base columns from the existing script
    base_columns = [
        'page_id', 
        'text_id',
        'title',
        'original_title',
        'full_bibliographic_entry',
        'year',
        'publisher',
        'location',
        'language',
        'page_count',
    ]
    
    # Add catalog_number columns only if they were created and have different values from text_id
    if 'catalog_number_1' in df.columns and df['catalog_number_1'].astype(str).ne("").any():
        base_columns.insert(2, 'catalog_number_1')
        if 'catalog_number_2' in df.columns and df['catalog_number_2'].astype(str).ne("").any():
            base_columns.insert(3, 'catalog_number_2')
    
    # Add clean_content column
    base_columns.append('clean_content')
    
    # Add content item columns (up to 3 items)
    content_item_columns = []
    for i in range(1, 4):
        item_cols = [
            f'content_item_{i}_title',
            f'content_item_{i}_original_title',
            f'content_item_{i}_translator',
            f'content_item_{i}_pages',
        ]
        content_item_columns.extend([col for col in item_cols if col in df.columns])
    
    # Add category and metadata columns
    category_columns = [
        'categories',
        'main_category',
        'time_period',
    ]
    
    # Combine all columns
    all_columns = base_columns + content_item_columns + category_columns
    
    # Check which columns are actually available
    available_columns = [col for col in all_columns if col in df.columns]
    
    # Create the final dataframe
    final_df = df[available_columns].copy()
    
    # Replace NaN values with empty strings for cleaner spreadsheet viewing
    for col in final_df.columns:
        if final_df[col].dtype == 'object':
            final_df[col] = final_df[col].fillna("")
        elif col in ['year', 'page_count']:
            # Convert numeric NaN to empty string
            final_df[col] = final_df[col].apply(lambda x: "" if pd.isna(x) else x)
    
    log_dataframe_info(final_df, "Final dataset for manual editing")
    
    # 9. Verify encoding quality
    logger.info("Step 9: Verifying encoding quality")
    
    # Check for remaining problematic encoding patterns
    problematic_patterns = [
        'Ã', 'Ä', 'Å', 'á¸', 'á¹', 'č', 'viá¸', 'Bhč', 'Mč', 'ā­'
    ]
    
    encoding_issues = {}
    for col in ['title', 'original_title', 'clean_content']:
        if col in final_df.columns:
            pattern_count = sum(final_df[col].astype(str).str.contains('|'.join(problematic_patterns), regex=True))
            if pattern_count > 0:
                encoding_issues[col] = pattern_count
                
                # Log examples of problematic entries
                problematic_entries = final_df[final_df[col].astype(str).str.contains('|'.join(problematic_patterns), regex=True)]
                if not problematic_entries.empty:
                    logger.warning(f"Encoding issues found in {col}, examples:")
                    for i, (idx, row) in enumerate(problematic_entries.head(3).iterrows()):
                        logger.warning(f"  {i+1}. {row[col]}")
    
    if encoding_issues:
        logger.warning(f"Potential encoding issues remain in {len(encoding_issues)} columns: {encoding_issues}")
        
        # Additional deep cleaning pass for problematic entries
        for col in encoding_issues.keys():
            mask = final_df[col].astype(str).str.contains('|'.join(problematic_patterns), regex=True)
            final_df.loc[mask, col] = final_df.loc[mask, col].apply(lambda x: fix_encoding_deep(fix_encoding_deep(x)))
            
        # Check if issues were resolved
        remaining_issues = sum(final_df['title'].astype(str).str.contains('|'.join(problematic_patterns), regex=True))
        logger.info(f"After deep cleaning, remaining issues: {remaining_issues}")
    else:
        logger.info("No obvious encoding issues detected in cleaned dataset")
    
    # 10. Export
    logger.info(f"Step 10: Exporting enhanced cleaned data to {output_file}")
    final_df.to_csv(output_file, index=False, encoding='utf-8')
    
    logger.info("Enhanced cleaning process completed successfully")
    return final_df

def validate_output(df):
    """Perform validation checks on the cleaned output"""
    validation_results = {
        "total_records": len(df),
        "columns": df.columns.tolist(),
        "missing_values": {col: df[col].isna().sum() for col in df.columns},
        "empty_strings": {col: (df[col] == "").sum() for col in df.columns if df[col].dtype == 'object'},
        "encoding_issues": {}
    }
    
    # Check for potential encoding issues
    problematic_patterns = ['Ã', 'Ä', 'Å', 'á¸', 'á¹', 'č', 'ā­']
    for col in df.columns:
        if df[col].dtype == 'object':
            pattern_count = df[col].astype(str).str.contains('|'.join(problematic_patterns), regex=True).sum()
            if pattern_count > 0:
                validation_results["encoding_issues"][col] = pattern_count
    
    return validation_results

if __name__ == "__main__":
    # Configuration (could be moved to a config file)
    input_file = "zweig_bibliography_cleaned_20250411_1024.csv"
    output_file = "zweig_bibliography_enhanced.csv"
    
    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} not found")
        exit(1)
    
    # Run the enhanced cleaning process
    cleaned_df = clean_zweig_bibliography(input_file, output_file)
    
    # Validate the output
    validation_results = validate_output(cleaned_df)
    
    # Output a summary report
    logger.info("\nEnhanced Cleaning Summary Report:")
    logger.info(f"Input file: {input_file}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Total records processed: {len(cleaned_df)}")
    logger.info(f"Character encoding issues fixed in text columns")
    logger.info(f"Wiki markup completely removed from content")
    logger.info(f"Enhanced bibliographic data extracted from content")
    logger.info(f"Content items with original titles and translators extracted")
    logger.info(f"Comprehensive encoding fixes applied to handle multilingual content")
    logger.info(f"Clean, comprehensive structure created for manual editing")
    
    # Log validation results
    logger.info("\nValidation Results:")
    logger.info(f"Total columns in final dataset: {len(validation_results['columns'])}")
    
    if validation_results["encoding_issues"]:
        logger.warning(f"Potential remaining encoding issues in {len(validation_results['encoding_issues'])} columns:")
        for col, count in validation_results["encoding_issues"].items():
            logger.warning(f"  - {col}: {count} records")
    else:
        logger.info("No obvious encoding issues detected in final dataset")
    
    # Display some sample rows from the cleaned dataset
    logger.info("\nSample rows from enhanced cleaned dataset for manual editing:")
    sample_rows = cleaned_df.head(3)
    for i, row in sample_rows.iterrows():
        logger.info(f"\nRow {i}:")
        for col in row.index:
            logger.info(f"{col}: {row[col]}")