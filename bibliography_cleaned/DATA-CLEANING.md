# DATA-CLEANING.md: Zweig Bibliography Cleaning Guide (Enhanced Version)

## 1. Dataset Structure Overview
The Zweig bibliography dataset (5,652 entries) contains bibliographic information with the following key characteristics:

- Primary content types: Category (72.5%), Redirect (27.3%)
- Entry identification: Each entry has unique page_id and text_id
- Content storage: Both raw (content) and partially cleaned (content_cleaned) formats

## 2. Key Cleaning Challenges

### 2.1. Character Encoding Issues (27.7% of entries)

#### 2.1.1. Arabic transliteration problems:
- Incorrect: Ä€, Ä«, Å«, á¹£, á¸¥, etc.
- Correct: Ā, ī, ū, ṣ, ḥ, etc.

#### 2.1.2. German and European language character problems:
- Incorrect: Ã¤, Ã¶, Ã¼, ÃŸ, etc.
- Correct: ä, ö, ü, ß, etc.

#### 2.1.3. Spanish and Latin character problems:
- Incorrect: Ã¡, Ã©, Ã­, Ã³, Ãº, Ã±, etc.
- Correct: á, é, í, ó, ú, ñ, etc.

#### 2.1.4. Cyrillic transliteration problems:
- Incorrect: ā­, iā­, skiā­, shteā­n
- Correct: ĭ, iĭ, skiĭ, shteĭn
- Example: "Arskiā­" should be "Arskiĭ" and "Bernshteā­n" should be "Bernshteĭn"

#### 2.1.5. Smart quotes/dashes problems:
- Incorrect: â€™, â€œ, â€, â€"
- Correct: ', ", ", -

### 2.2. Structural Issues
- Unnecessary columns: page_title (100% NULL)
- Embedded metadata: Categories stored within content as wiki markup
- Complex formatting: <lst>, [[]], HTML elements, and wiki syntax in content
- Inconsistent titles: No clear title field; titles embedded in content or redirect targets

### 2.3. Data Quality Problems
- Duplicates: 9.01% duplicate entries based on content_cleaned
- Missing values: High rates in language (98.8%), publisher (92.4%), page_count (82.4%)
- Wiki markup in content: Makes content difficult to read and edit manually

### 2.4. Multilingual Bibliography Entries
- Works translated into Russian from German with original titles in brackets
- Collections combining multiple works under one entry
- Transliterated titles that appear only in the Contents section rather than the main title
- Example pattern:
  - Main entry: "[Rausch der Verwandlung * Joseph Fouché. Bildnis eines politischen Menschen]"
  - Contents section: "Kristina Khoflener. Roman [Rausch der Verwandlung]" and "Zhozef Fushe. Portret politicheskogo deiatelia [Joseph Fouché. Bildnis eines politischen Menschen]"

## 3. Required Cleaning Operations

### 3.1. Initial Preprocessing
- Remove page_title column
- Check data types and ensure consistency

### 3.2. Text Normalization
- Fix character encoding in all text fields (Arabic, German, Spanish, Cyrillic characters, smart quotes)
- Apply multiple encoding fix passes for particularly difficult cases
- Use specialized patterns for each script/language family
- Apply to all text columns

### 3.3. Wiki Markup Removal
- Remove category tags, DEFAULTSORTKEY tags, link syntax
- Convert formatting (bold, italic) to plain text
- Clean up newlines and extra spaces
- Remove escaped quotes

### 3.4. Metadata Extraction
- Extract categories to separate field
- Format categories for readability
- Add main category classification based on first segment before "/"

### 3.5. Enhanced Title Extraction
- For translated works, extract both transliterated title (primary) and original title (secondary)
- For collections of works, combine titles from the Contents section
- Handle cases where the transliterated title appears only in the Contents section
- Prioritize transliterated titles over original titles for the main title field
- Extract translator information when available

### 3.6. Derived Fields
- Add time period classification:
  - Pre-Zweig (before 1881)
  - During Lifetime (1881-1942)
  - Post-WWII (1943-1980)
  - Late 20th Century (1981-2000)
  - Contemporary (after 2000)

### 3.7. Empty Value Standardization
- Replace NaN values with empty strings for text fields
- Convert numeric NaN values to empty strings for year and page_count

### 3.8. Content Item Extraction
- Extract individual works from collections into structured fields
- For each content item, extract:
  - Transliterated title
  - Original title
  - Translator information
  - Page ranges
- Handle various formats of Contents sections
- Support up to 3 content items per entry

### 3.9. Deep Encoding Verification
- Implement multiple passes of encoding fixes for complex cases
- Verify encoding quality after initial cleaning
- Identify and fix problematic patterns that persist after initial cleaning
- Apply targeted fixes for specific language patterns (Cyrillic, Indic, Arabic)

## 4. Enhanced Output Structure

Expanded structure for comprehensive bibliographic data:

- page_id: Reference ID
- text_id: Reference ID
- title: Clean, readable title (prioritizing transliterated titles)
- original_title: Original language title
- full_bibliographic_entry: Complete citation information
- year: Publication year
- publisher: Publisher information
- location: Publication location
- language: Language of the work
- page_count: Number of pages
- clean_content: Content with wiki markup removed
- content_item_X_title: Title of each content item (X=1,2,3)
- content_item_X_original_title: Original title of each content item
- content_item_X_translator: Translator of each content item
- content_item_X_pages: Page range of each content item
- categories: Categories formatted as readable text
- main_category: Main category
- time_period: Time period classification
- last_edited_date: Last wiki edit date

## 5. Cleaning Process Order
1. Data Loading and Initial Assessment
2. Structural Cleaning
3. Content Normalization
4. Metadata Enhancement
5. Content Item Extraction
6. Title and Original Title Extraction
7. Content Cleaning
8. Quality Verification
9. Output Preparation
10. Export

## 6. Verification Steps
After cleaning, verify:
- Character encoding issues fixed in sample records
- Wiki markup completely removed from content
- Clean, readable titles extracted correctly, especially for translated works
- Original titles preserved in separate field
- Content items properly extracted and structured
- Categories correctly extracted and formatted
- Time periods accurately assigned
- Empty values consistently represented
- Overall data quality and readability

## 7. Note on Missing Data
This cleaning process does not attempt to fill in missing values for:
- language (98.8%)
- publisher (92.4%)
- location (74.4%)
- page_count (82.4%)

These fields remain as empty strings in the output, ready for manual editing.

## 8. Advanced Processing Techniques

### 8.1. Multi-Pass Encoding Fixes
- Apply multiple encoding fix passes for particularly difficult cases
- Use specialized patterns for each script/language family

### 8.2. Context-Aware Extraction
- Use information from one field to improve extraction of another
- Extract titles based on Contents sections when main titles are unclear

### 8.3. Validation and Quality Control
- Verify encoding quality throughout the cleaning process
- Identify and report problematic entries
- Apply targeted cleaning to identified problem areas

## 9. Common Issues and Solutions

### 9.1. Transliterated Titles Missing
- When transliterated titles are missing from the main entry text but appear in the Contents section, extract and combine them from content items.
- Example: Extract "Kristina Khoflener. Roman * Zhozef Fushe. Portret politicheskogo deiatelia" from the Contents section when the main title only contains "[Rausch der Verwandlung * Joseph Fouché. Bildnis eines politischen Menschen]".

### 9.2. Complex Character Encoding
- Apply multiple passes of encoding fixes
- Use specialized fixes for Cyrillic transliteration (particularly for patterns like "iā­" that should be "iĭ")
- Verify and re-clean problematic entries

### 9.3. Publisher Extraction
- Look for publisher patterns with specific identifiers like "Izdatel'stvo", "Verlag", "Publishing", "Éditions"
- Handle publishers in quotation marks
- Extract location information from common city names even when not followed by colons