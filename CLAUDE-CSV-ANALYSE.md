# Stefan Zweig Bibliography Analysis

## Overview

This document provides detailed analysis instructions for the bibliographic data extracted from the Klawiter database on Stefan Zweig. The analysis script (`analyse-csv-output.py`) processes CSV exports to gain insights into the bibliography's structure, content types, and metadata patterns.

## Script Purpose

The script is designed to:

1. Automatically locate and analyze the latest CSV export file
2. Generate comprehensive statistics and visualizations
3. Extract structured bibliographic metadata
4. Categorize content types and analyze patterns
5. Record all findings in a detailed log file
6. Create visual representations of key distribution patterns

## Analysis Components

### 1. Basic Statistics
- Total number of entries
- Unique pages count
- Content length distribution (min, max, average)
- BLOB distribution statistics
- Flags distribution
- Redirect count

### 2. Content Type Analysis
The script classifies entries into the following categories:
- **Redirects**: Pages that simply redirect to other entries
- **Categories**: Category definition pages
- **Bibliography Entries**: Actual bibliographic content
- **Essays**: Essay descriptions and references
- **Translations**: Translation information
- **Unknown**: Content that doesn't match the defined patterns

### 3. Bibliographic Data Extraction
The script extracts structured metadata from the content field:
- Titles (from triple quotes pattern)
- Publication years
- Publishers
- Locations
- Translators
- Page counts
- Original titles (for translations)

### 4. Language Distribution Analysis
The script analyzes the language distribution in the bibliography by identifying language patterns:
- German content (identified through keywords like "Verlag", "Band", etc.)
- English content
- French content
- Spanish content
- Italian content
- Russian content
- Arabic content
- Other/unknown languages

### 5. Work References Analysis
The script counts references to Zweig's major works, including:
- Die Welt von Gestern
- Schachnovelle
- Brief einer Unbekannten
- Angst
- Amok
- Brennendes Geheimnis
- Sternstunden der Menschheit
- And other significant works

### 6. Publication Timeline Analysis
The script creates a timeline of publication years by:
- Extracting all years mentioned in the content
- Creating a chronological distribution
- Identifying peak publication periods
- Comparing publications during Zweig's lifetime (1881-1942) vs. posthumous

### 7. Category Structure Analysis
The script maps the category hierarchy by:
- Extracting all category tags
- Counting frequency of each category
- Analyzing the hierarchical structure
- Identifying top-level and sub-categories

## Visualizations

The script creates several visualizations saved to the `bibliography_analysis` directory:

1. **content_type_distribution.png**: Bar chart showing distribution of content types
2. **content_length_distribution.png**: Histogram of content lengths
3. **blob_distribution.png**: Bar chart showing content distribution across BLOBs
4. **language_distribution.png**: Pie chart of language distribution
5. **publication_timeline.png**: Timeline of publication years with highlighting for Zweig's lifetime
6. **major_works_references.png**: Bar chart of references to major works
7. **top_categories.png**: Bar chart of the most common categories

## Output

The script produces:

1. **Log file** (`zweig_analysis_YYYYMMDD_HHMM.log`): Detailed analysis results
2. **Visualization folder** (`bibliography_analysis`): All generated charts
3. **Summary file** (`analysis_summary.json`): Condensed results in JSON format

## Technical Implementation

The script uses several Python libraries:
- **pandas**: For data loading and manipulation
- **matplotlib/seaborn**: For visualization
- **re**: For regular expression pattern matching
- **logging**: For detailed logging
- **glob**: For finding the latest CSV file

## Usage Instructions

1. Place the script in the same directory as the CSV export files
2. Run: `python analyse-csv-output.py`
3. Review the log file for detailed results
4. Examine the visualizations in the output directory

## Analysis Patterns

### Regular Expressions for Content Extraction

The script uses custom regex patterns to extract information:

- **Title pattern**: `r"'''(.*?)'''"`
- **Year pattern**: `r'\b(1[8-9]\d{2}|20[0-2]\d)\b'`
- **Publisher patterns**:
  ```
  r'(?:Verlag|Publisher|Press):\s*([\w\s&\.,]+)'
  r'(?:published by|verlegt bei)\s*([\w\s&\.,]+)'
  r'\b(?:Verlag|Publishers?)\b[^\n.]*?([\w\s&]+)(?:,|\.|$)'
  ```
- **Translator pattern**: `r'(?:Translated by|Übersetzt von|Translator)[:\s]+([^,\n.]+)'`
- **Page count pattern**: `r'(\d+)(?:\s*)p\.'`

## Detailed Output Format

The log file contains sections for each analysis type:

```
=== STARTING STEFAN ZWEIG BIBLIOGRAPHY ANALYSIS ===
Found latest CSV file: zweig_extraction_progress_20250410_1807.csv
Successfully loaded 1183 entries with UTF-8 encoding

=== BASIC STATISTICS ===
Total entries: 1183
Unique pages: 1183
Redirects: 328
Content length - Min: 22, Max: 1922, Avg: 376.21
BLOB distribution: {'5': 368, '6': 249, '7': 192, '4': 187, '3': 123, '1': 42, '2': 22}
Flags distribution: {'utf-8': 1183}

=== CONTENT TYPE ANALYSIS ===
Redirect: 328 entries (27.73%)
Category: 612 entries (51.73%)
Bibliography Entry: 153 entries (12.93%)
Essay: 24 entries (2.03%)
Translation: 19 entries (1.61%)
Unknown: 47 entries (3.97%)

=== BIBLIOGRAPHIC DATA EXTRACTION ===
Titles extracted: 184
Years extracted: 427
Publishers extracted: 89
Locations extracted: 263
Translators extracted: 17
Page counts extracted: 46

...
```