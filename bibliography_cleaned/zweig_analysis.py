#!/usr/bin/env python
# coding: utf-8

"""
Stefan Zweig Bibliography Analysis Script
----------------------------------------
Analyzes bibliography CSV files and outputs detailed statistics to logs.
"""

import pandas as pd
import numpy as np
import re
import json
from collections import Counter
import logging
import os
from datetime import datetime

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_filename = f"{log_dir}/zweig_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger()

# Function to convert NumPy/Pandas objects to JSON-serializable types
def convert_to_serializable(obj):
    """Convert NumPy types to serializable Python types"""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.to_dict()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    else:
        return obj

def load_and_analyze_bibliography(file_path):
    """Analyze a bibliography CSV file and log statistics"""
    logger.info(f"Starting analysis of file: {file_path}")
    
    # Load CSV file
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Successfully loaded {len(df)} entries")
    except Exception as e:
        logger.error(f"Error loading file: {e}")
        return None, None
    
    # Basic dataset info
    logger.info(f"DataFrame shape: {df.shape}")
    
    # Check for missing values
    missing_values = df.isnull().sum()
    missing_percentage = (df.isnull().sum() / len(df)) * 100
    
    logger.info("\n--- MISSING VALUES ANALYSIS ---")
    for column, count in missing_values.items():
        logger.info(f"{column}: {count} missing values ({missing_percentage[column]:.2f}%)")
    
    # Content type analysis
    logger.info("\n--- CONTENT TYPE DISTRIBUTION ---")
    content_types = df['content_type'].value_counts()
    for content_type, count in content_types.items():
        logger.info(f"{content_type}: {count} entries ({count/len(df)*100:.2f}%)")
    
    # Temporal analysis
    logger.info("\n--- TEMPORAL ANALYSIS ---")
    
    # Years with data
    years_df = df[df['year'].notnull()]
    logger.info(f"Entries with year information: {len(years_df)} ({len(years_df)/len(df)*100:.2f}%)")
    
    # Year range
    year_range = {}
    if not years_df.empty:
        min_year = int(years_df['year'].min())
        max_year = int(years_df['year'].max())
        logger.info(f"Year range: {min_year} to {max_year} ({max_year-min_year+1} years)")
        year_range = {"min": min_year, "max": max_year, "span": max_year-min_year+1}
        
        # Publications by decade
        logger.info("\n--- PUBLICATIONS BY DECADE ---")
        decades = (years_df['year'] // 10 * 10).astype(int).value_counts().sort_index()
        decades_dict = {}
        for decade, count in decades.items():
            decade_str = f"{decade}s"
            logger.info(f"{decade_str}: {count} publications")
            decades_dict[decade_str] = int(count)
        
        # Time periods
        logger.info("\n--- TIME PERIODS ---")
        period_conditions = [
            (years_df['year'] < 1881),
            ((years_df['year'] >= 1881) & (years_df['year'] <= 1942)),
            ((years_df['year'] > 1942) & (years_df['year'] <= 1980)),
            ((years_df['year'] > 1980) & (years_df['year'] <= 2000)),
            (years_df['year'] > 2000)
        ]
        period_labels = [
            "Pre-Zweig (before 1881)",
            "During Lifetime (1881-1942)",
            "Post-WWII (1943-1980)",
            "Late 20th Century (1981-2000)",
            "Contemporary (after 2000)"
        ]
        periods = {}
        for label, condition in zip(period_labels, period_conditions):
            count = condition.sum()
            logger.info(f"{label}: {count} publications")
            periods[label] = int(count)
    else:
        decades_dict = {}
        periods = {}
    
    # Geographic analysis
    logger.info("\n--- GEOGRAPHIC ANALYSIS ---")
    
    # Publication locations
    loc_df = df[df['location'].notnull()]
    logger.info(f"Entries with location information: {len(loc_df)} ({len(loc_df)/len(df)*100:.2f}%)")
    
    locations_dict = {}
    if not loc_df.empty:
        locations = loc_df['location'].value_counts()
        logger.info("\n--- TOP 20 PUBLICATION LOCATIONS ---")
        for i, (location, count) in enumerate(locations.head(20).items()):
            logger.info(f"{location}: {count} publications")
            locations_dict[location] = int(count)
    
    # Extract and analyze categories
    logger.info("\n--- CATEGORY ANALYSIS ---")
    
    def extract_categories(text):
        """Extract categories from content using regex"""
        if pd.isna(text):
            return []
        categories = re.findall(r'\[\[Category:(.*?)\]\]', text)
        return categories
    
    df['extracted_categories'] = df['content'].apply(extract_categories)
    
    # Count entries with categories
    entries_with_categories = df[df['extracted_categories'].apply(lambda x: len(x) > 0)]
    logger.info(f"Entries with categories: {len(entries_with_categories)} ({len(entries_with_categories)/len(df)*100:.2f}%)")
    
    # Extract all categories and count them
    all_categories = [cat for sublist in df['extracted_categories'] for cat in sublist if sublist]
    category_counts = Counter(all_categories)
    
    categories_dict = {}
    logger.info("\n--- TOP 20 CATEGORIES ---")
    for category, count in category_counts.most_common(20):
        logger.info(f"{category}: {count} occurrences")
        categories_dict[category] = count
    
    # Extract main category (before first slash)
    def extract_main_category(categories):
        if not categories:
            return None
        
        first_cat = categories[0]
        match = re.match(r'([^/]+)', first_cat)
        if match:
            return match.group(1).strip()
        return first_cat
    
    df['main_category'] = df['extracted_categories'].apply(extract_main_category)
    main_categories = df['main_category'].value_counts()
    
    main_categories_dict = {}
    logger.info("\n--- MAIN CATEGORY TYPES ---")
    for category, count in main_categories.head(10).items():
        if category:
            logger.info(f"{category}: {count} entries")
            main_categories_dict[category] = int(count)
    
    # Extract internal links
    logger.info("\n--- LINK ANALYSIS ---")
    
    def extract_internal_links(text):
        """Extract internal links from content using regex"""
        if pd.isna(text):
            return []
        
        # Look for patterns like [[Something]] but not [[Category:Something]]
        links = re.findall(r'\[\[(?!Category:)(.*?)\]\]', text)
        return links
    
    df['internal_links'] = df['content'].apply(extract_internal_links)
    df['link_count'] = df['internal_links'].apply(len)
    
    total_links = df['link_count'].sum()
    entries_with_links = len(df[df['link_count'] > 0])
    avg_links = df['link_count'].mean()
    max_links = df['link_count'].max()
    
    logger.info(f"Total internal links found: {total_links}")
    logger.info(f"Entries with at least one internal link: {entries_with_links}")
    logger.info(f"Average links per entry: {avg_links:.2f}")
    logger.info(f"Maximum links in a single entry: {max_links}")
    
    # Find most referenced works
    all_links = [link for sublist in df['internal_links'] for link in sublist if isinstance(sublist, list)]
    link_counts = Counter(all_links)
    
    top_references = {}
    logger.info("\n--- TOP 20 MOST REFERENCED WORKS ---")
    for link, count in link_counts.most_common(20):
        logger.info(f"{link}: {count} references")
        top_references[link] = count
    
    # Language analysis (try to extract from the language field)
    logger.info("\n--- LANGUAGE ANALYSIS ---")
    
    # Count entries with language information
    lang_df = df[df['language'].notnull()]
    logger.info(f"Entries with language information: {len(lang_df)} ({len(lang_df)/len(df)*100:.2f}%)")
    
    languages_dict = {}
    if not lang_df.empty:
        # Try to extract primary language from the beginning of the field
        def extract_primary_language(text):
            if pd.isna(text):
                return None
            
            # Most language fields start with the language name
            match = re.match(r'^([A-Za-z]+)', text)
            if match:
                return match.group(1)
            return "Unknown"
        
        df['primary_language'] = df['language'].apply(extract_primary_language)
        language_counts = df['primary_language'].value_counts()
        
        logger.info("\n--- PRIMARY LANGUAGES ---")
        for language, count in language_counts.head(15).items():
            if language and language != "Unknown":
                logger.info(f"{language}: {count} entries")
                languages_dict[language] = int(count)
    
    # Page count analysis
    logger.info("\n--- PAGE COUNT ANALYSIS ---")
    
    # Count entries with page count information
    page_df = df[df['page_count'].notnull()].copy()
    logger.info(f"Entries with page count information: {len(page_df)} ({len(page_df)/len(df)*100:.2f}%)")
    
    page_stats = {}
    page_distribution = {}
    if not page_df.empty:
        min_pages = page_df['page_count'].min()
        max_pages = page_df['page_count'].max()
        avg_pages = page_df['page_count'].mean()
        median_pages = page_df['page_count'].median()
        
        logger.info(f"Minimum page count: {min_pages}")
        logger.info(f"Maximum page count: {max_pages}")
        logger.info(f"Average page count: {avg_pages:.2f}")
        logger.info(f"Median page count: {median_pages}")
        
        page_stats = {
            "min": float(min_pages),
            "max": float(max_pages),
            "avg": float(avg_pages),
            "median": float(median_pages)
        }
        
        # Page count distribution
        bins = [0, 10, 50, 100, 200, 500, 1000, float('inf')]
        labels = ['1-10', '11-50', '51-100', '101-200', '201-500', '501-1000', '1000+']
        
        # Use loc to avoid SettingWithCopyWarning
        page_df.loc[:, 'page_range'] = pd.cut(page_df['page_count'], bins=bins, labels=labels)
        page_ranges = page_df['page_range'].value_counts().sort_index()
        
        logger.info("\n--- PAGE COUNT DISTRIBUTION ---")
        for page_range, count in page_ranges.items():
            logger.info(f"{page_range}: {count} entries ({count/len(page_df)*100:.2f}%)")
            page_distribution[str(page_range)] = int(count)
    
    # Publication type analysis by decade
    decade_content_dict = {}
    if not years_df.empty:
        logger.info("\n--- CONTENT TYPES BY DECADE ---")
        
        # Group by decade and content type
        decade_content = years_df.groupby([(years_df['year'] // 10 * 10), 'content_type']).size().unstack(fill_value=0)
        
        # Log the results
        for decade, row in decade_content.iterrows():
            decade_str = f"{int(decade)}s"
            content_str = ", ".join([f"{content}: {count}" for content, count in row.items() if count > 0])
            logger.info(f"{decade_str}: {content_str}")
            
            # Store for JSON output
            decade_content_dict[decade_str] = {
                content: int(count) for content, count in row.items() if count > 0
            }
        
        # Category distribution by time period
        logger.info("\n--- CATEGORY DISTRIBUTION BY TIME PERIOD ---")
        
        # Create a copy of years_df to avoid SettingWithCopyWarning
        period_df = years_df.copy()
        
        # Add time period to period_df
        period_df.loc[:, 'time_period'] = 'Pre-Zweig'
        period_df.loc[(period_df['year'] >= 1881) & (period_df['year'] <= 1942), 'time_period'] = 'During Lifetime'
        period_df.loc[(period_df['year'] > 1942) & (period_df['year'] <= 1980), 'time_period'] = 'Post-WWII'
        period_df.loc[(period_df['year'] > 1980) & (period_df['year'] <= 2000), 'time_period'] = 'Late 20th Century'
        period_df.loc[period_df['year'] > 2000, 'time_period'] = 'Contemporary'
        
        # Merge with main categories
        period_df = period_df.merge(df[['content_cleaned', 'main_category']], on='content_cleaned', how='left')
        
        # Group by time period and main category
        period_category = period_df.groupby(['time_period', 'main_category']).size().unstack(fill_value=0)
        
        period_categories_dict = {}
        # Get the top 5 categories for each period
        for period, row in period_category.iterrows():
            top_categories = row.sort_values(ascending=False).head(5)
            category_str = ", ".join([f"{category}: {count}" for category, count in top_categories.items() if count > 0])
            logger.info(f"{period} - Top 5 categories: {category_str}")
            
            # Store for JSON output
            period_categories_dict[period] = {
                str(category): int(count) for category, count in top_categories.items() if count > 0
            }
    
    # Check for potential duplicates
    logger.info("\n--- DUPLICATE ANALYSIS ---")
    
    # Check for duplicate content
    content_dupes = df[df.duplicated(subset=['content'], keep=False)]
    logger.info(f"Entries with duplicate content: {len(content_dupes)} ({len(content_dupes)/len(df)*100:.2f}%)")
    
    # Check for duplicate content_cleaned
    cleaned_dupes = df[df.duplicated(subset=['content_cleaned'], keep=False)]
    logger.info(f"Entries with duplicate cleaned content: {len(cleaned_dupes)} ({len(cleaned_dupes)/len(df)*100:.2f}%)")
    
    duplication_stats = {
        "duplicate_content": int(len(content_dupes)),
        "duplicate_content_pct": float(len(content_dupes)/len(df)*100),
        "duplicate_cleaned": int(len(cleaned_dupes)),
        "duplicate_cleaned_pct": float(len(cleaned_dupes)/len(df)*100)
    }
    
    # Save summary statistics to JSON file
    logger.info("\n--- GENERATING SUMMARY STATISTICS ---")
    
    stats = {
        "file_name": os.path.basename(file_path),
        "total_entries": len(df),
        "content_types": {str(k): int(v) for k, v in content_types.items()},
        "missing_data": {
            column: {
                "count": int(count),
                "percentage": float(missing_percentage[column])
            } for column, count in missing_values.items()
        },
        "temporal": {
            "year_range": year_range,
            "by_decade": decades_dict,
            "by_period": periods,
            "content_by_decade": decade_content_dict,
            "categories_by_period": period_categories_dict
        },
        "geographic": {
            "top_locations": locations_dict
        },
        "categories": {
            "top_categories": categories_dict,
            "main_categories": main_categories_dict
        },
        "links": {
            "total_links": int(total_links),
            "entries_with_links": int(entries_with_links),
            "avg_links_per_entry": float(avg_links),
            "max_links": int(max_links),
            "top_referenced": top_references
        },
        "languages": languages_dict,
        "page_counts": {
            "stats": page_stats,
            "distribution": page_distribution
        },
        "duplication": duplication_stats
    }
    
    # Save to JSON file
    stats_file = f"zweig_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, default=convert_to_serializable)
        logger.info(f"Statistics saved to {stats_file}")
    except Exception as e:
        logger.error(f"Error saving statistics to JSON: {e}")
    
    return df, stats

def compare_bibliography_files(files, stats_list):
    """Compare multiple bibliography files and log differences"""
    if len(files) <= 1:
        return
    
    logger.info("\n--- COMPARING BIBLIOGRAPHY FILES ---")
    
    # Compare file sizes
    file_sizes = [os.path.getsize(file) for file in files]
    logger.info(f"File sizes: {list(zip(files, file_sizes))}")
    
    if len(set(file_sizes)) == 1:
        logger.info("All files have the same size")
    else:
        logger.info("Files have different sizes")
    
    # Compare entry counts
    entry_counts = [stats["total_entries"] for stats in stats_list]
    if len(set(entry_counts)) == 1:
        logger.info(f"All files have the same number of entries: {entry_counts[0]}")
    else:
        logger.info(f"Files have different entry counts: {list(zip(files, entry_counts))}")
    
    # Compare content types
    logger.info("\n--- CONTENT TYPE COMPARISON ---")
    for i, stats in enumerate(stats_list):
        logger.info(f"File {i+1}: {files[i]}")
        for content_type, count in stats["content_types"].items():
            logger.info(f"  {content_type}: {count}")

def main():
    """Main function to analyze all bibliography files"""
    logger.info("=== STEFAN ZWEIG BIBLIOGRAPHY ANALYSIS ===")
    
    # Find all CSV files with 'zweig_bibliography' in the name
    csv_files = [f for f in os.listdir('.') if f.startswith('zweig_bibliography') and f.endswith('.csv')]
    
    if not csv_files:
        logger.error("No bibliography CSV files found")
        return
    
    logger.info(f"Found {len(csv_files)} bibliography files to analyze")
    
    # Analyze each file
    dfs = []
    stats_list = []
    
    for file in csv_files:
        df, stats = load_and_analyze_bibliography(file)
        if df is not None:
            dfs.append(df)
            stats_list.append(stats)
    
    # Compare files if multiple were found
    if len(csv_files) > 1 and len(stats_list) > 1:
        compare_bibliography_files(csv_files, stats_list)
    
    logger.info("Analysis complete")

if __name__ == "__main__":
    main()