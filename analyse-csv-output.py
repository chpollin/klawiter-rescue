#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Stefan Zweig Bibliography Analysis Script (Improved Version)
This script analyzes CSV exports from the Klawiter database extraction process,
providing comprehensive insights into the bibliography structure.

Simply run this script in the same directory as your CSV files.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import os
import json
from collections import Counter
import numpy as np
from datetime import datetime
import logging
import glob

# Configure logging
log_filename = f'zweig_analysis_{datetime.now().strftime("%Y%m%d_%H%M")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

# Output directory for visualizations
OUTPUT_DIR = 'bibliography_analysis'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_latest_csv():
    """Find and load the latest CSV file in the current directory"""
    # Find all CSV files matching the extraction pattern
    csv_files = glob.glob("zweig_extraction*.csv")
    
    if not csv_files:
        logging.error("No CSV files found with 'zweig_extraction' pattern")
        return None
    
    # Find the latest file by modification time
    latest_file = max(csv_files, key=os.path.getmtime)
    logging.info(f"Found latest CSV file: {latest_file}")
    
    try:
        df = pd.read_csv(latest_file, encoding='utf-8')
        logging.info(f"Successfully loaded {len(df)} entries with UTF-8 encoding")
    except UnicodeDecodeError:
        # Try alternative encoding if UTF-8 fails
        df = pd.read_csv(latest_file, encoding='latin1')
        logging.info(f"Successfully loaded {len(df)} entries with Latin-1 encoding")
    
    # Clean up any NaN values
    df = df.fillna('')
    
    return df

def basic_statistics(df):
    """Generate basic statistics about the dataset"""
    stats = {
        'total_entries': len(df),
        'unique_pages': df['page_id'].nunique(),
        'content_stats': {
            'min_length': df['content'].str.len().min(),
            'max_length': df['content'].str.len().max(),
            'avg_length': df['content'].str.len().mean(),
            'median_length': df['content'].str.len().median()
        },
        'blob_distribution': df['blob_id'].value_counts().to_dict(),
        'flags_distribution': df['flags'].value_counts().to_dict()
    }
    
    # Count redirects
    redirect_pattern = r'^#REDIRECT'
    stats['redirects'] = df['content'].str.contains(redirect_pattern, regex=True).sum()
    
    logging.info("=== BASIC STATISTICS ===")
    logging.info(f"Total entries: {stats['total_entries']}")
    logging.info(f"Unique pages: {stats['unique_pages']}")
    logging.info(f"Redirects: {stats['redirects']}")
    logging.info(f"Content length - Min: {stats['content_stats']['min_length']}, Max: {stats['content_stats']['max_length']}, Avg: {stats['content_stats']['avg_length']:.2f}")
    logging.info(f"BLOB distribution: {stats['blob_distribution']}")
    logging.info(f"Flags distribution: {stats['flags_distribution']}")
    
    return stats

def identify_content_types(df):
    """Identify and categorize content types in the dataset"""
    # Add content type column
    df['content_type'] = 'Unknown'
    
    # Identify redirects (do this first since it's a clear pattern)
    redirect_pattern = r'^#REDIRECT'
    df.loc[df['content'].str.contains(redirect_pattern, regex=True), 'content_type'] = 'Redirect'
    
    # Identify categories
    category_pattern = r'\[\[Category:'
    df.loc[(df['content'].str.contains(category_pattern, regex=True)) & 
           (df['content_type'] == 'Unknown'), 'content_type'] = 'Category'
    
    # Identify bibliography entries - be more specific with patterns
    bibliography_patterns = [
        r'<lst type=bracket', 
        r"'''.*?'''",  # Triple quotes typically indicate title 
        r'\b(Volumes?|Band|Tome)\b',
        r'\b(Published|Veröffentlicht|Erschienen)\b',
        r'\d+\s*p\.'  # Page count pattern
    ]
    
    for pattern in bibliography_patterns:
        mask = (df['content'].str.contains(pattern, regex=True)) & (df['content_type'] == 'Unknown')
        df.loc[mask, 'content_type'] = 'Bibliography Entry'
    
    # Identify essays
    essay_pattern = r'\b(Essay|Essays|Aufsatz|Aufsätze)\b'
    mask = (df['content'].str.contains(essay_pattern, regex=True)) & (df['content_type'] == 'Unknown')
    df.loc[mask, 'content_type'] = 'Essay'
    
    # Identify translations
    translation_pattern = r'\b(Translation|Translated|Übersetzt|Translated by|Translator|Übersetzung)\b'
    mask = (df['content'].str.contains(translation_pattern, regex=True)) & (df['content_type'] == 'Unknown')
    df.loc[mask, 'content_type'] = 'Translation'
    
    # Identify poetry
    poetry_pattern = r'\b(Poem|Gedicht|Poetry|Poesie|Lyrik)\b'
    mask = (df['content'].str.contains(poetry_pattern, regex=True)) & (df['content_type'] == 'Unknown')
    df.loc[mask, 'content_type'] = 'Poetry'
    
    # Identify correspondence
    correspondence_pattern = r'\b(Letter|Brief|Correspondence|Korrespondenz)\b'
    mask = (df['content'].str.contains(correspondence_pattern, regex=True)) & (df['content_type'] == 'Unknown')
    df.loc[mask, 'content_type'] = 'Correspondence'
    
    # Count content types
    content_type_counts = df['content_type'].value_counts().to_dict()
    
    logging.info("=== CONTENT TYPE ANALYSIS ===")
    for content_type, count in content_type_counts.items():
        logging.info(f"{content_type}: {count} entries ({count/len(df)*100:.2f}%)")
    
    return df, content_type_counts

def extract_bibliographic_data(df):
    """Extract structured bibliographic data from content"""
    # Create columns for extracted data
    bibliographic_fields = [
        'title', 'year', 'publisher', 'location', 'language', 
        'translator', 'page_count', 'original_title'
    ]
    
    for field in bibliographic_fields:
        df[field] = ''
    
    # Extract titles - try multiple patterns
    # First try triple quotes pattern (most common)
    title_pattern1 = r"'''(.*?)'''"
    titles_found = 0
    
    for idx, row in df.iterrows():
        # Try triple quotes pattern first
        matches = re.findall(title_pattern1, row['content'])
        if matches:
            df.at[idx, 'title'] = matches[0]
            titles_found += 1
            continue
            
        # If no match, try page title if available
        if 'page_title' in df.columns and row['page_title']:
            # Convert underscores to spaces
            title = row['page_title'].replace('_', ' ')
            # Remove any REDIRECT patterns
            if not title.startswith('#REDIRECT'):
                df.at[idx, 'title'] = title
                titles_found += 1
                continue
                
        # Try first line if it's not a category or redirect
        if not row['content'].startswith(('#REDIRECT', '[[Category')):
            lines = row['content'].strip().split('\n')
            if lines:
                first_line = lines[0].strip()
                if len(first_line) > 3 and len(first_line) < 100:  # Reasonable title length
                    df.at[idx, 'title'] = first_line
                    titles_found += 1
    
    # Extract years using regex
    year_pattern = r'\b(1[8-9]\d{2}|20[0-2]\d)\b'
    df['year'] = df['content'].apply(
        lambda x: ', '.join(re.findall(year_pattern, x)[:3]) if re.findall(year_pattern, x) else ''
    )
    
    # Extract publishers with improved patterns
    publisher_patterns = [
        r'(?:Verlag|Publisher|Press):\s*([\w\s&\.,\-]+)',
        r'(?:published by|verlegt bei)\s*([\w\s&\.,\-]+)',
        r'\b(?:Verlag|Publishers?)\b[^\n.]*?([\w\s&\.,\-]+)(?:,|\.|$)',
        r'\b(?:Editions?|Edizioni)\b[^\n.]*?([\w\s&\.,\-]+)(?:,|\.|$)'
    ]
    
    def extract_publisher(text):
        for pattern in publisher_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return ''
    
    df['publisher'] = df['content'].apply(extract_publisher)
    
    # Extract locations with expanded list
    common_locations = [
        'Wien', 'Berlin', 'Frankfurt', 'Leipzig', 'London', 'New York', 
        'Paris', 'Zürich', 'Hamburg', 'München', 'Salzburg', 'Stockholm',
        'Amsterdam', 'Bern', 'Genf', 'Rome', 'Madrid', 'Barcelona',
        'Milano', 'Torino', 'Moskva', 'Moskau', 'Moscow', 'Praha', 'Prag', 'Prague',
        'Budapest', 'Tokyo', 'Warszawa', 'Warsaw', 'Buenos Aires', 'Rio de Janeiro'
    ]
    
    # Create regex pattern with word boundaries
    location_pattern = '|'.join(r'\b' + re.escape(loc) + r'\b' for loc in common_locations)
    
    df['location'] = df['content'].apply(
        lambda x: ', '.join(set(re.findall(location_pattern, x, re.IGNORECASE))) if re.findall(location_pattern, x, re.IGNORECASE) else ''
    )
    
    # Extract translator information with improved pattern
    translator_patterns = [
        r'(?:Translated by|Übersetzt von|Translator|Translation by)[:\s]+([^,\n.]+)',
        r'(?:Traduction|Traduit par|Traduzione di|Traducción de)[:\s]+([^,\n.]+)'
    ]
    
    def extract_translator(text):
        for pattern in translator_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ''
    
    df['translator'] = df['content'].apply(extract_translator)
    
    # Extract page count with improved pattern
    page_patterns = [
        r'(\d+)(?:\s*)p\.',
        r'(\d+)(?:\s*)pages',
        r'(\d+)(?:\s*)Seiten'
    ]
    
    def extract_page_count(text):
        for pattern in page_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ''
    
    df['page_count'] = df['content'].apply(extract_page_count)
    
    # Extract original title for translations with improved pattern
    original_patterns = [
        r'(?:Original title|Originally published as)[:\s]+(.*?)(?:\.|$|\n)',
        r'(?:Originaltitel|Ursprünglicher Titel)[:\s]+(.*?)(?:\.|$|\n)',
        r'(?:Titre original|Título original)[:\s]+(.*?)(?:\.|$|\n)'
    ]
    
    def extract_original_title(text):
        for pattern in original_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ''
    
    df['original_title'] = df['content'].apply(extract_original_title)
    
    # Extract language with improved pattern
    language_patterns = [
        r'(?:Language|Sprache|Langue|Idioma)[:\s]+(.*?)(?:\.|$|\n)',
        r'(?:in|auf|en|in the|translated into)\s+(German|English|French|Spanish|Italian|Russian|Chinese|Japanese|Arabic|Portuguese)\b'
    ]
    
    def extract_language(text):
        for pattern in language_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ''
    
    df['language'] = df['content'].apply(extract_language)
    
    logging.info("=== BIBLIOGRAPHIC DATA EXTRACTION ===")
    logging.info(f"Titles extracted: {titles_found}")
    logging.info(f"Years extracted: {sum(df['year'] != '')}")
    logging.info(f"Publishers extracted: {sum(df['publisher'] != '')}")
    logging.info(f"Locations extracted: {sum(df['location'] != '')}")
    logging.info(f"Translators extracted: {sum(df['translator'] != '')}")
    logging.info(f"Page counts extracted: {sum(df['page_count'] != '')}")
    logging.info(f"Languages explicitly mentioned: {sum(df['language'] != '')}")
    
    # Log some example entries
    logging.info("=== SAMPLE ENTRIES ===")
    sample_entries = df[df['title'] != ''].sample(min(5, sum(df['title'] != ''))).reset_index(drop=True)
    for _, row in sample_entries.iterrows():
        logging.info(f"- Title: {row['title']}")
        if row['year']: logging.info(f"  Year: {row['year']}")
        if row['publisher']: logging.info(f"  Publisher: {row['publisher']}")
        if row['location']: logging.info(f"  Location: {row['location']}")
        if row['translator']: logging.info(f"  Translator: {row['translator']}")
        if row['page_count']: logging.info(f"  Pages: {row['page_count']}")
        logging.info("")
    
    return df

def analyze_language_distribution(df):
    """Analyze the language distribution in the bibliography"""
    # Identify language patterns in content with expanded patterns
    language_patterns = {
        'German': [
            r'\b(German|Deutsch)\b', 
            r'\b(Verlag|Band|herausgegeben)\b',
            r'\b(München|Berlin|Frankfurt|Leipzig|Wien)\b'
        ],
        'English': [
            r'\b(English|translated into English)\b', 
            r'\b(London|New York|Oxford|Cambridge)\b',
            r'\b(Publisher|Press)\b'
        ],
        'French': [
            r'\b(French|Français|traduit en français)\b', 
            r'\b(Paris|Éditions)\b',
            r'\b(traduction|traduit)\b'
        ],
        'Spanish': [
            r'\b(Spanish|Español|traducido al español)\b', 
            r'\b(Madrid|Barcelona|Buenos Aires)\b',
            r'\b(traducción|traducido)\b'
        ],
        'Italian': [
            r'\b(Italian|Italiano|tradotto in italiano)\b', 
            r'\b(Roma|Milano|Torino|Firenze)\b',
            r'\b(traduzione|tradotto)\b'
        ],
        'Russian': [
            r'\b(Russian|русский|переведено на русский)\b',
            r'\b(Moscow|Moskva|Moskau)\b'
        ],
        'Arabic': [
            r'\b(Arabic|العربية)\b', 
            r'(تولستوي|زفايج)',
            r'\b(ترجمة|المترجم)\b'
        ],
        'Chinese': [
            r'\b(Chinese|中文|汉语)\b',
            r'\b(北京|上海|台北)\b',
            r'(译者|翻译)'
        ],
        'Other': []  # Catch-all
    }
    
    def detect_language(text):
        """Detect the language of the content"""
        # First check if explicit language is mentioned in the content
        explicit_patterns = [
            r'\b(German|English|French|Spanish|Italian|Russian|Arabic|Chinese) (edition|translation|version)\b',
            r'\b(translated into|translated to|translation into) (German|English|French|Spanish|Italian|Russian|Arabic|Chinese)\b',
            r'\b(auf Deutsch|in English|en français|en español|in italiano|на русском|بالعربية|用中文)\b'
        ]
        
        for pattern in explicit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Check which group contains the language name
                if len(match.groups()) >= 2:
                    return match.group(2)  # Second group has language name
                else:
                    return match.group(1)  # First group has language name
        
        # If no explicit mention, try pattern matching
        for lang, patterns in language_patterns.items():
            match_count = 0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    match_count += 1
            
            # Require at least 2 pattern matches for more confidence
            if match_count >= 2:
                return lang
                
        # Check if language is in the category
        category_match = re.search(r'\[\[Category:.*?\((German|English|French|Spanish|Italian|Russian|Arabic|Chinese)\)\]\]', text)
        if category_match:
            return category_match.group(1)
            
        return 'Unknown'
    
    df['detected_language'] = df['content'].apply(detect_language)
    
    language_distribution = df['detected_language'].value_counts().to_dict()
    
    logging.info("=== LANGUAGE DISTRIBUTION ===")
    for language, count in language_distribution.items():
        logging.info(f"{language}: {count} entries ({count/len(df)*100:.2f}%)")
    
    return language_distribution

def analyze_work_references(df):
    """Analyze references to Zweig's major works with improved matching"""
    # List of major Zweig works to search for (with variations)
    major_works = {
        'Die Welt von Gestern': [r'Die Welt von Gestern', r'World of Yesterday', r'Monde d\'hier'],
        'Schachnovelle': [r'Schachnovelle', r'Chess Story', r'Chess Novella', r'Royal Game', r'Jeu d\'échecs'],
        'Brief einer Unbekannten': [r'Brief einer Unbekannten', r'Letter from an Unknown Woman', r'Lettre d\'une inconnue'],
        'Angst': [r'Angst', r'Fear', r'Amok', r'Peur'],
        'Amok': [r'Amok', r'Amok-Läufer', r'Amok Runner'],
        'Brennendes Geheimnis': [r'Brennendes Geheimnis', r'Burning Secret'],
        'Sternstunden der Menschheit': [r'Sternstunden der Menschheit', r'Decisive Moments', r'Moments étoilés'],
        'Marie Antoinette': [r'Marie Antoinette', r'María Antonieta', r'Marie-Antoinette'],
        'Joseph Fouché': [r'Joseph Fouché', r'Fouche', r'Fouché'],
        'Ungeduld des Herzens': [r'Ungeduld des Herzens', r'Beware of Pity', r'Impatience du cœur'],
        'Verwirrung der Gefühle': [r'Verwirrung der Gefühle', r'Confusion of Feelings', r'Confusion des sentiments'],
        'Der Kampf mit dem Dämon': [r'Kampf mit dem Dämon', r'Struggle with the Daemon'],
        'Drei Meister': [r'Drei Meister', r'Three Masters'],
        'Rausch der Verwandlung': [r'Rausch der Verwandlung', r'Post-Office Girl'],
        'Clarissa': [r'Clarissa'],
        'Maria Stuart': [r'Maria Stuart', r'Mary Stuart', r'Marie Stuart'],
        'Magellan': [r'Magellan', r'Magallanes', r'Magellan: Der Mann und seine Tat'],
        'Erasmus von Rotterdam': [r'Erasmus', r'Erasmus von Rotterdam', r'Érasme']
    }
    
    work_references = {work: 0 for work in major_works.keys()}
    
    # Count references to each work with all variations
    for work, patterns in major_works.items():
        count = 0
        for pattern in patterns:
            # Use word boundaries and case-insensitive matching
            regex_pattern = r'\b' + pattern + r'\b'
            matches = df['content'].str.contains(regex_pattern, regex=True, case=False)
            count += matches.sum()
        work_references[work] = count
    
    # Sort by frequency
    work_references = {k: v for k, v in sorted(work_references.items(), key=lambda item: item[1], reverse=True)}
    
    logging.info("=== REFERENCES TO MAJOR WORKS ===")
    for work, count in work_references.items():
        if count > 0:
            logging.info(f"{work}: {count} references")
    
    return work_references

def analyze_publication_timeline(df):
    """Analyze the publication timeline based on years mentioned in content"""
    # Extract all years from content
    all_years = []
    year_pattern = r'\b(1[8-9]\d{2}|20[0-2]\d)\b'
    
    for content in df['content']:
        years = re.findall(year_pattern, content)
        if years:
            all_years.extend(years)
    
    # Convert to integers and filter valid range
    all_years = [int(year) for year in all_years if 1850 <= int(year) <= 2025]
    
    # Count frequency of each year
    year_counts = Counter(all_years)
    
    # Sort by year
    timeline = {year: count for year, count in sorted(year_counts.items())}
    
    # Identify significant periods
    zweig_lifetime = {year: count for year, count in timeline.items() if 1881 <= year <= 1942}
    post_zweig = {year: count for year, count in timeline.items() if year > 1942}
    
    logging.info("=== PUBLICATION TIMELINE ===")
    logging.info(f"Years mentioned: {len(timeline)} distinct years")
    
    # Find years with highest frequency
    top_years = sorted(timeline.items(), key=lambda x: x[1], reverse=True)[:10]
    logging.info("Most frequently mentioned years:")
    for year, count in top_years:
        logging.info(f"{year}: {count} mentions")
    
    # Summarize during/after Zweig's life
    lifetime_count = sum(zweig_lifetime.values())
    post_count = sum(post_zweig.values())
    total_count = lifetime_count + post_count
    if total_count > 0:
        logging.info(f"Mentions during Zweig's lifetime (1881-1942): {lifetime_count} ({lifetime_count/total_count*100:.2f}%)")
        logging.info(f"Mentions after Zweig's death: {post_count} ({post_count/total_count*100:.2f}%)")
    
    return {
        'timeline': timeline,
        'zweig_lifetime': zweig_lifetime,
        'post_zweig': post_zweig,
        'top_years': top_years
    }

def analyze_category_structure(df):
    """Analyze the category structure in the bibliography"""
    # Extract categories
    category_pattern = r'\[\[Category:(.*?)(?:\|.*?)?\]\]'
    
    categories = []
    for content in df['content']:
        matches = re.findall(category_pattern, content)
        categories.extend(matches)
    
    # Count frequency
    category_counts = Counter(categories)
    
    # Hierarchical structure analysis
    hierarchy = {}
    for category in category_counts:
        parts = category.split('/')
        current = hierarchy
        for part in parts:
            part = part.strip()
            if part not in current:
                current[part] = {}
            current = current[part]
    
    logging.info("=== CATEGORY STRUCTURE ===")
    logging.info(f"Unique categories: {len(category_counts)}")
    
    # Log top categories
    top_categories = category_counts.most_common(15)
    logging.info("Most common categories:")
    for category, count in top_categories:
        logging.info(f"{category}: {count} entries")
    
    # Log main category branches
    logging.info("Main category branches:")
    for main_branch in hierarchy:
        subcategories = len(hierarchy[main_branch])
        logging.info(f"{main_branch}: {subcategories} subcategories")
    
    return {
        'category_counts': category_counts,
        'hierarchy': hierarchy,
        'top_categories': top_categories
    }

def generate_visualizations(results, df):
    """Generate visualizations based on analysis results"""
    logging.info("=== GENERATING VISUALIZATIONS ===")
    
    # Set up visualization style
    sns.set(style="whitegrid")
    plt.rcParams.update({'figure.max_open_warning': 0})
    
    # 1. Content type distribution
    plt.figure(figsize=(12, 7))
    content_types = list(results['content_type_counts'].keys())
    counts = list(results['content_type_counts'].values())
    
    # Sort the content types by count for better visualization
    sorted_indices = np.argsort(counts)[::-1]
    sorted_content_types = [content_types[i] for i in sorted_indices]
    sorted_counts = [counts[i] for i in sorted_indices]
    
    bars = plt.bar(sorted_content_types, sorted_counts, color=sns.color_palette("viridis", len(content_types)))
    plt.title('Content Type Distribution', fontsize=14)
    plt.ylabel('Number of Entries', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    # Add count labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{int(height)}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'content_type_distribution.png'), dpi=300)
    plt.close()
    logging.info("Created visualization: content_type_distribution.png")
    
    # 2. Content length distribution
    plt.figure(figsize=(12, 7))
    sns.histplot(df['content'].str.len(), bins=30, kde=True)
    plt.title('Content Length Distribution', fontsize=14)
    plt.xlabel('Length (characters)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'content_length_distribution.png'), dpi=300)
    plt.close()
    logging.info("Created visualization: content_length_distribution.png")
    
    # 3. BLOB distribution
    plt.figure(figsize=(12, 7))
    blob_ids = list(results['basic_stats']['blob_distribution'].keys())
    blob_counts = list(results['basic_stats']['blob_distribution'].values())
    
    # Make sure blob_ids are strings for proper sorting
    blob_ids = [str(b) for b in blob_ids]
    
    # Sort them numerically
    sorted_indices = np.argsort([int(b) for b in blob_ids])
    sorted_blob_ids = [blob_ids[i] for i in sorted_indices]
    sorted_blob_counts = [blob_counts[i] for i in sorted_indices]
    
    bars = plt.bar(sorted_blob_ids, sorted_blob_counts, color=sns.color_palette("mako", len(blob_ids)))
    plt.title('Content Distribution by BLOB', fontsize=14)
    plt.xlabel('BLOB ID', fontsize=12)
    plt.ylabel('Number of Entries', fontsize=12)
    
    # Add count labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{int(height)}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'blob_distribution.png'), dpi=300)
    plt.close()
    logging.info("Created visualization: blob_distribution.png")
    
    # 4. Language distribution
    plt.figure(figsize=(12, 9))
    languages = list(results['language_distribution'].keys())
    lang_counts = list(results['language_distribution'].values())
    
    # Sort for better visualization (keep Unknown at the end)
    if 'Unknown' in languages:
        unknown_idx = languages.index('Unknown')
        unknown_count = lang_counts[unknown_idx]
        languages.pop(unknown_idx)
        lang_counts.pop(unknown_idx)
        
        # Sort the rest by count
        sorted_indices = np.argsort(lang_counts)[::-1]
        languages = [languages[i] for i in sorted_indices] + ['Unknown']
        lang_counts = [lang_counts[i] for i in sorted_indices] + [unknown_count]
    else:
        # Sort all by count
        sorted_indices = np.argsort(lang_counts)[::-1]
        languages = [languages[i] for i in sorted_indices]
        lang_counts = [lang_counts[i] for i in sorted_indices]
    
# Create a pie chart without Unknown for better visualization
    if 'Unknown' in languages:
        non_unknown_languages = [l for l in languages if l != 'Unknown']
        non_unknown_counts = [c for l, c in zip(languages, lang_counts) if l != 'Unknown']
        
        # Only create pie chart if we have meaningful data
        if sum(non_unknown_counts) > 0:
            plt.figure(figsize=(12, 9))
            plt.pie(non_unknown_counts, labels=non_unknown_languages, autopct='%1.1f%%', startangle=90, 
                    colors=sns.color_palette("Set2", len(non_unknown_languages)),
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1})
            plt.title('Language Distribution (Excluding Unknown)', fontsize=14)
            plt.axis('equal')
            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, 'language_distribution.png'), dpi=300)
            plt.close()
    else:
        plt.figure(figsize=(12, 9))
        plt.pie(lang_counts, labels=languages, autopct='%1.1f%%', startangle=90, 
                colors=sns.color_palette("Set2", len(languages)),
                wedgeprops={'edgecolor': 'white', 'linewidth': 1})
        plt.title('Language Distribution', fontsize=14)
        plt.axis('equal')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'language_distribution.png'), dpi=300)
        plt.close()
    
    # Also create a bar chart with all languages for completeness
    plt.figure(figsize=(12, 7))
    bars = plt.bar(languages, lang_counts, color=sns.color_palette("Set2", len(languages)))
    plt.title('Language Distribution (All)', fontsize=14)
    plt.ylabel('Number of Entries', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    # Add count labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{int(height)}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'language_distribution_bar.png'), dpi=300)
    plt.close()
    
    logging.info("Created visualization: language_distribution.png")
    
    # 5. Publication timeline
    if results['publication_timeline']['timeline']:
        plt.figure(figsize=(16, 8))
        years = list(results['publication_timeline']['timeline'].keys())
        counts = list(results['publication_timeline']['timeline'].values())
        
        # Highlight Zweig's lifetime
        lifetime_mask = [(1881 <= year <= 1942) for year in years]
        plt.bar([y for i, y in enumerate(years) if lifetime_mask[i]], 
                [c for i, c in enumerate(counts) if lifetime_mask[i]], 
                color='#1f77b4', label="During Zweig's lifetime (1881-1942)")
        plt.bar([y for i, y in enumerate(years) if not lifetime_mask[i]], 
                [c for i, c in enumerate(counts) if not lifetime_mask[i]], 
                color='#ff7f0e', label="After Zweig's death")
        
        plt.title('Publication Years Mentioned in Bibliography', fontsize=14)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add annotations for significant years
        significant_years = {
            1881: "Zweig's birth",
            1942: "Zweig's death",
            1928: "Volpone premiere",
            1939: "Exile to England",
            1941: "Move to Brazil"
        }
        
        for year, event in significant_years.items():
            if year in results['publication_timeline']['timeline']:
                height = results['publication_timeline']['timeline'][year]
                plt.annotate(event, xy=(year, height), xytext=(year, height+max(counts)*0.05),
                            arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=8),
                            horizontalalignment='center', verticalalignment='bottom')
        
        # Improve x-axis ticks for readability
        # If we have many years, show only every 5th or 10th year
        if len(years) > 30:
            tick_step = 10 if len(years) > 60 else 5
            plt.xticks([y for i, y in enumerate(sorted(set(years))) if i % tick_step == 0], rotation=45)
        
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'publication_timeline.png'), dpi=300)
        plt.close()
        logging.info("Created visualization: publication_timeline.png")
        
        # Also create a histogram for decades
        plt.figure(figsize=(14, 7))
        # Convert years to decades
        decades = [int(year/10)*10 for year in years]
        decade_counts = Counter(decades)
        
        # Sort by decade
        sorted_decades = sorted(decade_counts.keys())
        decade_values = [decade_counts[d] for d in sorted_decades]
        
        # Highlight Zweig's lifetime decades
        lifetime_mask = [(1880 <= decade <= 1940) for decade in sorted_decades]
        bars1 = plt.bar([f"{d}s" for i, d in enumerate(sorted_decades) if lifetime_mask[i]], 
                      [c for i, c in enumerate(decade_values) if lifetime_mask[i]], 
                      color='#1f77b4', label="During Zweig's lifetime")
        bars2 = plt.bar([f"{d}s" for i, d in enumerate(sorted_decades) if not lifetime_mask[i]], 
                      [c for i, c in enumerate(decade_values) if not lifetime_mask[i]], 
                      color='#ff7f0e', label="After Zweig's death")
        
        plt.title('Publication Mentions by Decade', fontsize=14)
        plt.xlabel('Decade', fontsize=12)
        plt.ylabel('Number of Mentions', fontsize=12)
        plt.legend()
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'publication_by_decade.png'), dpi=300)
        plt.close()
        logging.info("Created visualization: publication_by_decade.png")
    
    # 6. Major works references
    plt.figure(figsize=(14, 8))
    # Filter to works that have at least one reference
    referenced_works = {k: v for k, v in results['work_references'].items() if v > 0}
    works = list(referenced_works.keys())[:15]  # Top 15 works
    work_counts = list(referenced_works.values())[:15]
    
    # Create horizontal bar chart
    bars = plt.barh(works, work_counts, color=sns.color_palette("rocket", len(works)))
    plt.title('References to Zweig\'s Major Works', fontsize=14)
    plt.xlabel('Number of References', fontsize=12)
    
    # Add count labels
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 1, bar.get_y() + bar.get_height()/2,
                f'{int(width)}', ha='left', va='center', fontsize=9)
    
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'major_works_references.png'), dpi=300)
    plt.close()
    logging.info("Created visualization: major_works_references.png")
    
    # 7. Category distribution (top categories)
    if results['category_structure']['category_counts']:
        plt.figure(figsize=(14, 10))
        top_categories = [cat for cat, count in results['category_structure']['top_categories']]
        cat_counts = [count for cat, count in results['category_structure']['top_categories']]
        
        # Shorten category names if too long
        short_names = []
        for cat in top_categories:
            if len(cat) > 40:
                parts = cat.split('/')
                if len(parts) > 1:
                    short_name = f"{parts[0]}/.../{parts[-1]}"
                else:
                    short_name = cat[:37] + "..."
                short_names.append(short_name)
            else:
                short_names.append(cat)
        
        # Create horizontal bar chart
        bars = plt.barh(short_names, cat_counts, color=sns.color_palette("flare", len(top_categories)))
        plt.title('Top Categories', fontsize=14)
        plt.xlabel('Number of Entries', fontsize=12)
        
        # Add count labels
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 1, bar.get_y() + bar.get_height()/2,
                    f'{int(width)}', ha='left', va='center', fontsize=9)
        
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'top_categories.png'), dpi=300)
        plt.close()
        logging.info("Created visualization: top_categories.png")
        
        # Create a treemap of main category branches
        try:
            # Only create treemap if we have matplotlib-compatible data
            main_branches = {}
            for branch, subcats in results['category_structure']['hierarchy'].items():
                # Count total entries in this branch
                branch_entries = sum(results['category_structure']['category_counts'][branch + "/" + subcat] 
                                     if branch + "/" + subcat in results['category_structure']['category_counts'] else 0
                                     for subcat in subcats)
                
                # Also add direct entries in this main category
                if branch in results['category_structure']['category_counts']:
                    branch_entries += results['category_structure']['category_counts'][branch]
                
                if branch_entries > 0:
                    main_branches[branch] = branch_entries
            
            if main_branches:
                # Sort by count
                main_branches = {k: v for k, v in sorted(main_branches.items(), 
                                                        key=lambda item: item[1], reverse=True)}
                
                plt.figure(figsize=(14, 10))
                labels = list(main_branches.keys())
                sizes = list(main_branches.values())
                
                # Create the treemap
                plt.rcParams.update({'font.size': 12})
                cmap = plt.cm.viridis
                mini = min(sizes)
                maxi = max(sizes)
                norm = plt.Normalize(mini, maxi)
                colors = [cmap(norm(value)) for value in sizes]
                
                # Calculate grid size
                rows = int(np.ceil(np.sqrt(len(labels))))
                cols = int(np.ceil(len(labels) / rows))
                
                gs = plt.GridSpec(rows, cols)
                
                for i, (label, size) in enumerate(zip(labels, sizes)):
                    row = i // cols
                    col = i % cols
                    
                    ax = plt.subplot(gs[row, col])
                    ax.set_xticks([])
                    ax.set_yticks([])
                    
                    # Create a color bar within each cell
                    rect = plt.Rectangle((0, 0), 1, 1, facecolor=colors[i])
                    ax.add_patch(rect)
                    
                    # Add main category name and count
                    ax.text(0.5, 0.5, label, ha='center', va='center', fontsize=12,
                            color='white' if np.mean(colors[i][:3]) < 0.5 else 'black')
                    ax.text(0.5, 0.3, f"{size} entries", ha='center', va='center', fontsize=10,
                            color='white' if np.mean(colors[i][:3]) < 0.5 else 'black')
                
                plt.suptitle('Main Category Branches', fontsize=16)
                plt.tight_layout(rect=[0, 0, 1, 0.96])
                plt.savefig(os.path.join(OUTPUT_DIR, 'category_branches.png'), dpi=300)
                plt.close()
                logging.info("Created visualization: category_branches.png")
                
        except Exception as e:
            logging.warning(f"Could not create category treemap: {str(e)}")
    
    logging.info(f"Visualizations saved to: {OUTPUT_DIR}")

def save_analysis_summary(results):
    """Save a summary of the analysis results to a JSON file"""
    summary_file = os.path.join(OUTPUT_DIR, 'analysis_summary.json')
    
    # Create a simplified summary with only the essential data
    # Convert any non-standard data types (like numpy int64) to Python native types
    def convert_to_serializable(obj):
        if isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, dict):
            return {str(k): convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(i) for i in obj]
        elif isinstance(obj, tuple):
            return [convert_to_serializable(i) for i in obj]
        else:
            return obj
    
    # Apply conversion to our data
    summary = {
        'basic_stats': convert_to_serializable(results['basic_stats']),
        'content_types': convert_to_serializable(results['content_type_counts']),
        'language_distribution': convert_to_serializable(results['language_distribution']),
        'top_works': convert_to_serializable({k: v for k, v in list(results['work_references'].items())[:10]}),
        'publication_timeline': {
            'top_years': convert_to_serializable(dict(results['publication_timeline']['top_years']))
        },
        'top_categories': convert_to_serializable(dict(results['category_structure']['top_categories']))
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Analysis summary saved to: {summary_file}")

def create_html_report(results, df):
    """Create a comprehensive HTML report of the analysis"""
    report_file = os.path.join(OUTPUT_DIR, 'zweig_bibliography_report.html')
    
    # Create a simple HTML with Bootstrap for styling
    html_content = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stefan Zweig Bibliography Analysis</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; }}
            .header {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
            .section {{ margin-bottom: 40px; }}
            .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .visualization {{ margin: 20px 0; text-align: center; }}
            .visualization img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Stefan Zweig Bibliography Analysis</h1>
                <p class="lead">Generated on {datetime.now().strftime("%Y-%m-%d at %H:%M")}</p>
            </div>
            
            <div class="section">
                <h2>Basic Statistics</h2>
                <div class="stats">
                    <p><strong>Total entries:</strong> {results['basic_stats']['total_entries']}</p>
                    <p><strong>Redirects:</strong> {results['basic_stats']['redirects']} ({results['basic_stats']['redirects']/results['basic_stats']['total_entries']*100:.2f}%)</p>
                    <p><strong>Content length:</strong> Min={results['basic_stats']['content_stats']['min_length']}, Max={results['basic_stats']['content_stats']['max_length']}, Avg={results['basic_stats']['content_stats']['avg_length']:.2f}</p>
                </div>
                
                <h3>Content Types</h3>
                <div class="visualization">
                    <img src="content_type_distribution.png" alt="Content Type Distribution">
                </div>
                
                <h3>Content Length Distribution</h3>
                <div class="visualization">
                    <img src="content_length_distribution.png" alt="Content Length Distribution">
                </div>
                
                <h3>BLOB Distribution</h3>
                <div class="visualization">
                    <img src="blob_distribution.png" alt="BLOB Distribution">
                </div>
            </div>
            
            <div class="section">
                <h2>Language Analysis</h2>
                <div class="visualization">
                    <img src="language_distribution.png" alt="Language Distribution">
                </div>
                <div class="visualization">
                    <img src="language_distribution_bar.png" alt="Language Distribution Bar Chart">
                </div>
            </div>
            
            <div class="section">
                <h2>Publication Timeline</h2>
                <div class="visualization">
                    <img src="publication_timeline.png" alt="Publication Timeline">
                </div>
                <div class="visualization">
                    <img src="publication_by_decade.png" alt="Publication by Decade">
                </div>
            </div>
            
            <div class="section">
                <h2>Major Works Analysis</h2>
                <div class="visualization">
                    <img src="major_works_references.png" alt="Major Works References">
                </div>
            </div>
            
            <div class="section">
                <h2>Category Structure</h2>
                <div class="visualization">
                    <img src="top_categories.png" alt="Top Categories">
                </div>
                <div class="visualization">
                    <img src="category_branches.png" alt="Category Branches">
                </div>
            </div>
            
            <div class="footer">
                <p>Analysis completed. Log file: {log_filename}</p>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logging.info(f"HTML report saved to: {report_file}")

def main():
    """Main function to run the analysis"""
    logging.info("=== STARTING STEFAN ZWEIG BIBLIOGRAPHY ANALYSIS ===")
    logging.info(f"Results will be saved to log file: {log_filename}")
    
    # Load data
    df = load_latest_csv()
    if df is None:
        logging.error("Failed to load data. Exiting.")
        return
    
    # Run analyses
    results = {}
    
    # Basic statistics
    results['basic_stats'] = basic_statistics(df)
    
    # Content type analysis
    df, results['content_type_counts'] = identify_content_types(df)
    
    # Extract bibliographic data
    df = extract_bibliographic_data(df)
    
    # Language distribution
    results['language_distribution'] = analyze_language_distribution(df)
    
    # Work references
    results['work_references'] = analyze_work_references(df)
    
    # Publication timeline
    results['publication_timeline'] = analyze_publication_timeline(df)
    
    # Category structure
    results['category_structure'] = analyze_category_structure(df)
    
    # Generate visualizations
    generate_visualizations(results, df)
    
    # Save analysis summary
    save_analysis_summary(results)
    
    # Create HTML report
    create_html_report(results, df)
    
    logging.info("=== ANALYSIS COMPLETE ===")
    logging.info(f"Log file: {log_filename}")
    logging.info(f"Visualizations and report: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()