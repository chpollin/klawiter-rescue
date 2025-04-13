#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import re
import os
from datetime import datetime
import logging
from collections import Counter

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

# Output directory for analysis reports
OUTPUT_DIR = 'bibliography_analysis'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_csv_file(file_path):
    """Load the CSV file and perform initial examination"""
    logging.info(f"Loading CSV file: {file_path}")
    
    try:
        # Try with UTF-8 encoding first
        df = pd.read_csv(file_path, encoding='utf-8')
        logging.info(f"Successfully loaded {len(df)} entries with UTF-8 encoding")
    except UnicodeDecodeError:
        # Try with alternative encoding if UTF-8 fails
        df = pd.read_csv(file_path, encoding='latin1')
        logging.info(f"Successfully loaded {len(df)} entries with Latin-1 encoding")
    
    # Print basic information about the dataset
    logging.info(f"DataFrame shape: {df.shape}")
    logging.info(f"Columns: {df.columns.tolist()}")
    
    # Check for missing values
    missing_values = df.isnull().sum()
    logging.info("Missing values per column:")
    for col, count in missing_values.items():
        if count > 0:
            logging.info(f"  {col}: {count} missing values ({count/len(df)*100:.2f}%)")
    
    return df

def analyze_content_types(df):
    """Analyze the distribution and characteristics of content types"""
    logging.info("=== CONTENT TYPE ANALYSIS ===")
    
    # Count content types
    content_type_counts = df['content_type'].value_counts()
    logging.info("Content type distribution:")
    for content_type, count in content_type_counts.items():
        logging.info(f"  {content_type}: {count} entries ({count/len(df)*100:.2f}%)")
    
    # Analyze content length by type
    logging.info("Content length statistics by type:")
    for content_type in content_type_counts.index:
        subset = df[df['content_type'] == content_type]
        stats = subset['content_length'].describe()
        logging.info(f"  {content_type}:")
        logging.info(f"    Count: {stats['count']}")
        logging.info(f"    Mean: {stats['mean']:.2f}")
        logging.info(f"    Min: {stats['min']}")
        logging.info(f"    Max: {stats['max']}")
    
    return content_type_counts

def analyze_redirect_entries(df):
    """Analyze redirect entries to understand their structure"""
    logging.info("=== REDIRECT ENTRIES ANALYSIS ===")
    
    # Filter to only redirect entries
    redirects_df = df[df['content'].str.startswith('#REDIRECT', na=False)]
    logging.info(f"Found {len(redirects_df)} redirect entries")
    
    # Extract redirect targets
    redirect_pattern = r'#REDIRECT\s*\[\[(.*?)\]\]'
    redirects_df['redirect_target'] = redirects_df['content'].str.extract(redirect_pattern, expand=False)
    
    # Check if all redirects were parsed correctly
    missing_targets = redirects_df['redirect_target'].isna().sum()
    logging.info(f"Redirects with unparsed targets: {missing_targets}")
    
    # Analyze which content types contain redirects
    redirect_content_types = redirects_df['content_type'].value_counts()
    logging.info("Content types of redirect entries:")
    for content_type, count in redirect_content_types.items():
        logging.info(f"  {content_type}: {count} entries ({count/len(redirects_df)*100:.2f}%)")
    
    # Sample some redirects
    if len(redirects_df) > 0:
        logging.info("Sample redirect entries:")
        sample = redirects_df.sample(min(5, len(redirects_df)))
        for _, row in sample.iterrows():
            logging.info(f"  Content: {row['content']}")
            logging.info(f"  Target: {row['redirect_target']}")
            logging.info(f"  Content Type: {row['content_type']}")
            logging.info("")
    
    return redirects_df

def analyze_bibliography_entries(df):
    """Analyze bibliography entries to understand their structure"""
    logging.info("=== BIBLIOGRAPHY ENTRIES ANALYSIS ===")
    
    # Filter to only bibliography entries
    biblio_df = df[df['content_type'] == 'Bibliography Entry']
    logging.info(f"Found {len(biblio_df)} bibliography entries")
    
    # Check for common patterns
    patterns = {
        'has_volumes_header': biblio_df['content'].str.contains('===Volumes===', regex=False).sum(),
        'has_triple_quotes': biblio_df['content'].str.contains("'''", regex=False).sum(),
        'has_lst_tag': biblio_df['content'].str.contains('<lst', regex=False).sum(),
        'has_publisher': biblio_df['publisher'].notna().sum(),
        'has_year': biblio_df['year'].notna().sum(),
        'has_location': biblio_df['location'].notna().sum(),
        'has_page_count': biblio_df['page_count'].notna().sum(),
        'is_redirect': biblio_df['content'].str.startswith('#REDIRECT', na=False).sum()
    }
    
    logging.info("Bibliography entry patterns:")
    for pattern, count in patterns.items():
        logging.info(f"  {pattern}: {count} entries ({count/len(biblio_df)*100:.2f}%)")
    
    # Sample some bibliography entries
    if len(biblio_df) > 0:
        logging.info("Sample bibliography entries:")
        sample = biblio_df.sample(min(3, len(biblio_df)))
        for _, row in sample.iterrows():
            logging.info(f"  Title: {row['content_title']}")
            logging.info(f"  Content: {row['content'][:200]}...")
            logging.info(f"  Year: {row['year']}")
            logging.info(f"  Publisher: {row['publisher']}")
            logging.info(f"  Location: {row['location']}")
            logging.info("")
    
    return biblio_df

def analyze_text_encoding_issues(df):
    """Analyze potential encoding issues in the text"""
    logging.info("=== TEXT ENCODING ANALYSIS ===")
    
    # Look for common encoding issue markers
    encoding_issues = {
        'contains_Ã¤': df['content'].str.contains('Ã¤', regex=False).sum(),
        'contains_Ã¶': df['content'].str.contains('Ã¶', regex=False).sum(),
        'contains_Ã¼': df['content'].str.contains('Ã¼', regex=False).sum(),
        'contains_Ãœ': df['content'].str.contains('Ãœ', regex=False).sum(),
        'contains_ÃŸ': df['content'].str.contains('ÃŸ', regex=False).sum(),
        'contains_Ã©': df['content'].str.contains('Ã©', regex=False).sum(),
        'contains_Ã¨': df['content'].str.contains('Ã¨', regex=False).sum(),
        'contains_Ã²': df['content'].str.contains('Ã²', regex=False).sum(),
        'contains_Ã¹': df['content'].str.contains('Ã¹', regex=False).sum()
    }
    
    logging.info("Potential encoding issues:")
    for issue, count in encoding_issues.items():
        if count > 0:
            logging.info(f"  {issue}: {count} entries ({count/len(df)*100:.2f}%)")
    
    # Check how many entries have any encoding issue
    any_encoding_issue = df['content'].str.contains('Ã', regex=False)
    total_affected = any_encoding_issue.sum()
    logging.info(f"Total entries with encoding issues: {total_affected} ({total_affected/len(df)*100:.2f}%)")
    
    # Check encoding issues by content type
    logging.info("Encoding issues by content type:")
    for content_type in df['content_type'].unique():
        subset = df[df['content_type'] == content_type]
        issues_count = subset['content'].str.contains('Ã', regex=False).sum()
        if len(subset) > 0:
            logging.info(f"  {content_type}: {issues_count} entries ({issues_count/len(subset)*100:.2f}%)")
    
    # Sample entries with encoding issues
    if total_affected > 0:
        logging.info("Sample entries with encoding issues:")
        
        # Create a mask for entries with any encoding issue
        encoding_mask = df['content'].str.contains('Ã', regex=False)
        sample = df[encoding_mask].sample(min(3, encoding_mask.sum()))
        
        for _, row in sample.iterrows():
            logging.info(f"  Page ID: {row['page_id']}")
            logging.info(f"  Content Type: {row['content_type']}")
            logging.info(f"  Title: {row['content_title']}")
            logging.info(f"  Content sample: {row['content'][:200]}...")
            logging.info("")
    
    return encoding_issues, total_affected

def analyze_category_structure(df):
    """Analyze the category entries to understand their structure and hierarchy"""
    logging.info("=== CATEGORY STRUCTURE ANALYSIS ===")
    
    # Filter to category entries
    category_df = df[df['content_type'] == 'Category']
    logging.info(f"Analyzing {len(category_df)} category entries")
    
    # Extract category names and hierarchy information
    category_pattern = r'\[\[Category:(.*?)(?:\|.*?)?\]\]'
    categories = []
    
    for content in category_df['content']:
        if pd.isna(content):
            continue
        matches = re.findall(category_pattern, content)
        categories.extend(matches)
    
    # Count category frequencies
    category_counts = Counter(categories)
    
    logging.info(f"Found {len(category_counts)} unique categories")
    logging.info("Top 10 categories:")
    for category, count in category_counts.most_common(10):
        logging.info(f"  {category}: {count} entries")
    
    # Analyze category hierarchy (categories with slashes)
    hierarchical = [cat for cat in category_counts if '/' in cat]
    logging.info(f"Found {len(hierarchical)} hierarchical categories")
    
    # Extract top-level categories (before first slash)
    top_level = {}
    for cat in category_counts:
        parts = cat.split('/')
        if parts[0] not in top_level:
            top_level[parts[0]] = 0
        top_level[parts[0]] += category_counts[cat]
    
    logging.info("Top-level categories:")
    for cat, count in sorted(top_level.items(), key=lambda x: x[1], reverse=True)[:10]:
        logging.info(f"  {cat}: {count} entries")
    
    # Sample some category entries
    if len(category_df) > 0:
        logging.info("Sample category entries:")
        sample = category_df.sample(min(3, len(category_df)))
        for _, row in sample.iterrows():
            logging.info(f"  Page ID: {row['page_id']}")
            logging.info(f"  Content Title: {row['content_title']}")
            logging.info(f"  Content: {row['content'][:200]}...")
            logging.info("")
    
    return category_counts, top_level

def analyze_year_distribution(df):
    """Analyze the distribution of years in the dataset"""
    logging.info("=== YEAR DISTRIBUTION ANALYSIS ===")
    
    # Count non-null years
    years_present = df['year'].notna().sum()
    logging.info(f"Entries with year information: {years_present} ({years_present/len(df)*100:.2f}%)")
    
    # Analyze year values
    if years_present > 0:
        # Convert years to numeric if they're not already
        if df['year'].dtype == 'object':
            # For multi-year entries, take the first year
            df['first_year'] = df['year'].str.extract(r'(\d{4})', expand=False)
            year_values = pd.to_numeric(df['first_year'], errors='coerce')
        else:
            year_values = df['year']
        
        # Calculate statistics
        year_stats = year_values.describe()
        logging.info(f"Year statistics:")
        logging.info(f"  Minimum: {year_stats['min']}")
        logging.info(f"  Maximum: {year_stats['max']}")
        logging.info(f"  Mean: {year_stats['mean']:.2f}")
        
        # Count by decade
        decades = (year_values // 10 * 10).dropna().astype(int)
        decade_counts = decades.value_counts().sort_index()
        
        logging.info("Distribution by decade:")
        for decade, count in decade_counts.items():
            logging.info(f"  {decade}s: {count} entries")
        
        # Check years during Zweig's lifetime (1881-1942) vs. posthumous
        during_lifetime = ((year_values >= 1881) & (year_values <= 1942)).sum()
        posthumous = (year_values > 1942).sum()
        
        if during_lifetime + posthumous > 0:
            lifetime_pct = during_lifetime / (during_lifetime + posthumous) * 100
            posthumous_pct = posthumous / (during_lifetime + posthumous) * 100
            
            logging.info("Publications during Zweig's lifetime vs. posthumous:")
            logging.info(f"  During lifetime (1881-1942): {during_lifetime} entries ({lifetime_pct:.2f}%)")
            logging.info(f"  Posthumous (after 1942): {posthumous} entries ({posthumous_pct:.2f}%)")
    
    return years_present

def analyze_language_field(df):
    """Analyze the language field and try to detect languages in content"""
    logging.info("=== LANGUAGE FIELD ANALYSIS ===")
    
    # Count non-null language entries
    languages_present = df['language'].notna().sum()
    logging.info(f"Entries with language information: {languages_present} ({languages_present/len(df)*100:.2f}%)")
    
    # Analyze language values
    if languages_present > 0:
        language_counts = df['language'].value_counts()
        
        logging.info("Language distribution:")
        for language, count in language_counts.items():
            logging.info(f"  {language}: {count} entries ({count/languages_present*100:.2f}%)")
    
    # Look for language indicators in content
    language_indicators = {
        'German': [r'\b(deutsch|deutsche|deutschen|auf deutsch)\b', r'\b(verlag)\b'],
        'English': [r'\b(english|translated into english)\b', r'\b(publisher|press)\b'],
        'French': [r'\b(français|française|en français)\b', r'\b(édition|traduit)\b'],
        'Spanish': [r'\b(español|española|en español)\b', r'\b(edición|traducido)\b'],
        'Italian': [r'\b(italiano|italiana|in italiano)\b', r'\b(edizione|traduzione)\b']
    }
    
    logging.info("Language indicators in content:")
    for language, patterns in language_indicators.items():
        combined_pattern = '|'.join(patterns)
        matches = df['content'].str.contains(combined_pattern, case=False, regex=True, na=False).sum()
        logging.info(f"  Potential {language} content: {matches} entries ({matches/len(df)*100:.2f}%)")
    
    return languages_present

def investigate_sample_entries(df, content_type, n=5):
    """Examine sample entries of a specific content type to understand patterns"""
    subset = df[df['content_type'] == content_type]
    if len(subset) == 0:
        logging.info(f"No entries found with content_type '{content_type}'")
        return
        
    logging.info(f"=== SAMPLE ANALYSIS: {content_type.upper()} ({len(subset)} entries) ===")
    sample = subset.sample(min(n, len(subset)))
    
    for idx, row in sample.iterrows():
        logging.info(f"Entry ID: {row['page_id']}")
        logging.info(f"Content Title: {row['content_title']}")
        logging.info(f"Content Length: {row['content_length']}")
        if 'year' in row and not pd.isna(row['year']):
            logging.info(f"Year: {row['year']}")
        if 'publisher' in row and not pd.isna(row['publisher']):
            logging.info(f"Publisher: {row['publisher']}")
        if 'location' in row and not pd.isna(row['location']):
            logging.info(f"Location: {row['location']}")
        logging.info(f"Content:\n{row['content']}")
        logging.info("-" * 50)

def analyze_wiki_markup_patterns(df):
    """Analyze MediaWiki formatting patterns in the content"""
    logging.info("=== WIKI MARKUP PATTERN ANALYSIS ===")
    
    # Define patterns to look for
    wiki_patterns = {
        'Triple quotes (bold)': r"'''.*?'''",
        'Double quotes (italic)': r"''.*?''",
        'Category tags': r'\[\[Category:.*?\]\]',
        'Wiki links': r'\[\[.*?\]\]',
        'Section headers': r'={2,}.*?={2,}',
        'List tags': r'<lst.*?>',
        'HTML-like tags': r'<[^>]+>',
        'URL links': r'https?://\S+'
    }
    
    # Count occurrences
    pattern_counts = {}
    for name, pattern in wiki_patterns.items():
        count = df['content'].str.contains(pattern, regex=True, na=False).sum()
        pattern_counts[name] = count
    
    logging.info("Wiki markup patterns found:")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        logging.info(f"  {pattern}: {count} entries ({count/len(df)*100:.2f}%)")
    
    # Analyze by content type
    logging.info("Markup patterns by content type:")
    for content_type in df['content_type'].unique():
        subset = df[df['content_type'] == content_type]
        if len(subset) == 0:
            continue
            
        logging.info(f"  {content_type} ({len(subset)} entries):")
        for name, pattern in wiki_patterns.items():
            count = subset['content'].str.contains(pattern, regex=True, na=False).sum()
            if count > 0:
                logging.info(f"    {name}: {count} entries ({count/len(subset)*100:.2f}%)")
    
    return pattern_counts

def analyze_blob_distribution(df):
    """Analyze the distribution of entries across BLOBs"""
    logging.info("=== BLOB DISTRIBUTION ANALYSIS ===")
    
    # Count entries per BLOB
    blob_counts = df['blob_id'].value_counts().sort_index()
    
    logging.info(f"Distribution across {len(blob_counts)} BLOBs:")
    for blob_id, count in blob_counts.items():
        logging.info(f"  BLOB {blob_id}: {count} entries ({count/len(df)*100:.2f}%)")
    
    # Analyze content types per BLOB
    logging.info("Content types by BLOB:")
    for blob_id in blob_counts.index:
        subset = df[df['blob_id'] == blob_id]
        content_type_counts = subset['content_type'].value_counts()
        
        logging.info(f"  BLOB {blob_id}:")
        for content_type, count in content_type_counts.items():
            logging.info(f"    {content_type}: {count} entries ({count/len(subset)*100:.2f}%)")
    
    return blob_counts

def write_summary_report(df, analysis_results):
    """Write a comprehensive summary report of all analyses"""
    logging.info("=== WRITING SUMMARY REPORT ===")
    
    report_file = os.path.join(OUTPUT_DIR, f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# STEFAN ZWEIG BIBLIOGRAPHY DATA ANALYSIS\n")
        f.write(f"Analysis performed: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        f.write("## DATASET OVERVIEW\n")
        f.write(f"Total entries: {len(df)}\n")
        f.write(f"Columns: {', '.join(df.columns)}\n\n")
        
        # Missing values
        f.write("## MISSING VALUES\n")
        missing_values = df.isnull().sum()
        for col, count in missing_values.items():
            if count > 0:
                f.write(f"{col}: {count} missing values ({count/len(df)*100:.2f}%)\n")
        f.write("\n")
        
        # Content types
        f.write("## CONTENT TYPE DISTRIBUTION\n")
        content_type_counts = df['content_type'].value_counts()
        for content_type, count in content_type_counts.items():
            f.write(f"{content_type}: {count} entries ({count/len(df)*100:.2f}%)\n")
        f.write("\n")
        
        # Redirect analysis
        f.write("## REDIRECT ENTRIES\n")
        redirects = df[df['content'].str.startswith('#REDIRECT', na=False)]
        f.write(f"Total redirects: {len(redirects)} ({len(redirects)/len(df)*100:.2f}%)\n")
        redirect_content_types = redirects['content_type'].value_counts()
        f.write("Redirects by content type:\n")
        for content_type, count in redirect_content_types.items():
            f.write(f"- {content_type}: {count} entries\n")
        f.write("\n")
        
        # Encoding issues
        f.write("## ENCODING ISSUES\n")
        any_encoding_issue = df['content'].str.contains('Ã', regex=False, na=False)
        total_affected = any_encoding_issue.sum()
        f.write(f"Total entries with encoding issues: {total_affected} ({total_affected/len(df)*100:.2f}%)\n\n")
        
        # BLOB distribution
        if 'blob_id' in df.columns:
            f.write("## BLOB DISTRIBUTION\n")
            blob_counts = df['blob_id'].value_counts().sort_index()
            for blob_id, count in blob_counts.items():
                f.write(f"BLOB {blob_id}: {count} entries ({count/len(df)*100:.2f}%)\n")
            f.write("\n")
        
        # Year distribution
        if 'year' in df.columns:
            f.write("## YEAR DISTRIBUTION\n")
            years_present = df['year'].notna().sum()
            f.write(f"Entries with year information: {years_present} ({years_present/len(df)*100:.2f}%)\n")
            if years_present > 0:
                # Convert years to numeric if they're not already
                if df['year'].dtype == 'object':
                    # For multi-year entries, take the first year
                    df['first_year'] = df['year'].str.extract(r'(\d{4})', expand=False)
                    year_values = pd.to_numeric(df['first_year'], errors='coerce')
                else:
                    year_values = df['year']
                
                # Calculate statistics
                year_stats = year_values.describe()
                f.write(f"Year range: {int(year_stats['min'])} - {int(year_stats['max'])}\n")
                
                # During Zweig's lifetime vs. posthumous
                during_lifetime = ((year_values >= 1881) & (year_values <= 1942)).sum()
                posthumous = (year_values > 1942).sum()
                
                if during_lifetime + posthumous > 0:
                    lifetime_pct = during_lifetime / (during_lifetime + posthumous) * 100
                    posthumous_pct = posthumous / (during_lifetime + posthumous) * 100
                    
                    f.write(f"During Zweig's lifetime (1881-1942): {during_lifetime} entries ({lifetime_pct:.2f}%)\n")
                    f.write(f"Posthumous (after 1942): {posthumous} entries ({posthumous_pct:.2f}%)\n")
            f.write("\n")
        
        # Recommendations
        f.write("## RECOMMENDATIONS FOR DATA CLEANING\n")
        
        # Redirects
        f.write("1. Redirects:\n")
        f.write(f"   - {len(redirects)} entries should be properly categorized as 'Redirect'\n")
        redirect_in_other = sum((df['content'].str.startswith('#REDIRECT', na=False)) & (df['content_type'] != 'Redirect'))
        if redirect_in_other > 0:
            f.write(f"   - {redirect_in_other} redirect entries are currently miscategorized\n")
        
        # Encoding
        f.write("2. Encoding Issues:\n")
        f.write(f"   - {total_affected} entries have encoding issues that need to be fixed\n")
        f.write("   - Common characters to fix: ä, ö, ü, ß, é\n")
        
        # Bibliography entries
        biblio_df = df[df['content_type'] == 'Bibliography Entry']
        if len(biblio_df) > 0:
            biblio_redirects = biblio_df['content'].str.startswith('#REDIRECT', na=False).sum()
            if biblio_redirects > 0:
                f.write("3. Bibliography Entries:\n")
                f.write(f"   - {biblio_redirects}/{len(biblio_df)} 'Bibliography Entry' entries are actually redirects\n")
        
        # Missing data
        f.write("4. Missing Data:\n")
        high_missing = [col for col, count in missing_values.items() if count/len(df) > 0.5]
        f.write(f"   - High missing values in: {', '.join(high_missing)}\n")
        f.write("   - Consider extracting this data from content text where possible\n")
        
        f.write("\n## CONCLUSION\n")
        f.write("This dataset requires significant cleaning, particularly addressing encoding issues, correctly categorizing redirects, and extracting structured data from the content text.")
    
    logging.info(f"Summary report written to: {report_file}")
    return report_file

def main():
    """Main function to run the data analysis"""
    logging.info("=== STARTING ZWEIG BIBLIOGRAPHY DATA ANALYSIS ===")
    
    # Specify the CSV file to analyze
    csv_file = "analysis_output/zweig_bibliography_enhanced_20250410_1911.csv"
    
    # Check if file exists
    if not os.path.exists(csv_file):
        logging.error(f"File not found: {csv_file}")
        logging.info("Please provide the correct path to the CSV file")
        return
    
    # Load the CSV file
    df = load_csv_file(csv_file)
    
    # Initialize results dictionary
    analysis_results = {}
    
    # Perform various analyses
    analysis_results['content_types'] = analyze_content_types(df)
    analysis_results['redirect_entries'] = analyze_redirect_entries(df)
    analysis_results['bibliography_entries'] = analyze_bibliography_entries(df)
    analysis_results['encoding_issues'] = analyze_text_encoding_issues(df)
    analysis_results['category_structure'] = analyze_category_structure(df)
    analysis_results['year_distribution'] = analyze_year_distribution(df)
    analysis_results['language_field'] = analyze_language_field(df)
    analysis_results['wiki_markup'] = analyze_wiki_markup_patterns(df)
    analysis_results['blob_distribution'] = analyze_blob_distribution(df)
    
    # Investigate samples of each content type
    for content_type in df['content_type'].unique():
        investigate_sample_entries(df, content_type, n=2)
    
    # Write summary report
    summary_file = write_summary_report(df, analysis_results)
    
    logging.info("=== DATA ANALYSIS COMPLETE ===")
    logging.info(f"Log file: {log_filename}")
    logging.info(f"Summary report: {summary_file}")

if __name__ == "__main__":
    main()