#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import logging
import os
import mysql.connector
import csv
from collections import Counter
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    filename=f'zweig_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add console handler for immediate feedback
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'klawiter'
}

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Analyze Stefan Zweig bibliography data')
    parser.add_argument('--csv', default=None, help='Path to CSV file with extracted data')
    parser.add_argument('--extract', action='store_true', help='Extract a sample of data directly from BLOBs')
    parser.add_argument('--sample-size', type=int, default=100, help='Number of entries to extract for sample')
    parser.add_argument('--output', default='analysis_output', help='Output directory for analysis results')
    parser.add_argument('--no-plots', action='store_true', help='Skip generating plots')
    return parser.parse_args()

def connect_to_db():
    """Establish database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        logging.info("Database connection established")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection error: {err}")
        raise

def analyze_extracted_data(csv_file, output_dir, generate_plots=True):
    """Analyze the extracted bibliography data"""
    logging.info(f"Analyzing extracted data from: {csv_file}")
    
    try:
        # Load the CSV data
        df = pd.read_csv(csv_file)
        logging.info(f"Loaded {len(df)} entries from CSV")
        
        # Basic metrics analysis
        logging.info("== Basic Metrics Analysis ==")
        logging.info(f"Total entries: {len(df)}")
        logging.info(f"Unique page IDs: {df['page_id'].nunique()}")
        if 'text_id' in df.columns:
            logging.info(f"Unique text IDs: {df['text_id'].nunique()}")
        
        # Content length analysis
        df['content_length'] = df['content'].apply(len)
        logging.info(f"Content length: min={df['content_length'].min()}, max={df['content_length'].max()}, avg={df['content_length'].mean():.2f}")
        
        # Flag distribution if available
        if 'flags' in df.columns:
            logging.info(f"Flag distribution: {df['flags'].value_counts().to_dict()}")
        
        # Content pattern analysis
        logging.info("== Content Pattern Analysis ==")
        
        # Helper function to identify patterns
        def find_content_patterns(content):
            patterns = {
                'has_title_markup': bool(re.search(r"'''.*?'''", content)),
                'has_volumes': 'Volumes' in content,
                'has_year': bool(re.search(r'\b(1[8-9]\d{2}|20[0-2]\d)\b', content)),
                'has_publisher': bool(re.search(r'(?:Verlag|Publisher|Press)', content, re.IGNORECASE)),
                'has_location': bool(re.search(r'(?:Wien|Berlin|Frankfurt|Leipzig|London|New York)', content)),
                'has_list': '<lst' in content,
                'has_html': bool(re.search(r'<\w+[^>]*>', content)),
                'has_category': '[[Category:' in content,
                'has_translation': bool(re.search(r'\b(translation|translated by|übersetzt)\b', content, re.IGNORECASE)),
                'has_review': bool(re.search(r'\b(review|reviewed|rezension)\b', content, re.IGNORECASE))
            }
            return patterns
        
        # Apply pattern analysis to all entries
        pattern_results = df['content'].apply(find_content_patterns)
        pattern_df = pd.DataFrame(pattern_results.tolist())
        
        # Log pattern results
        for col in pattern_df.columns:
            logging.info(f"{col}: {pattern_df[col].sum()} entries ({pattern_df[col].mean()*100:.2f}%)")
        
        # Extract titles from content
        logging.info("== Title Analysis ==")
        
        def extract_title_from_content(content):
            # Try to find title in triple quotes
            title_match = re.search(r"'''(.*?)'''", content)
            if title_match:
                return title_match.group(1)
            
            # Otherwise use first non-empty line
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            return lines[0] if lines else ""
        
        df['content_title'] = df['content'].apply(extract_title_from_content)
        
        # Check if page title and content title match
        if 'page_title' in df.columns:
            df['title_match'] = df.apply(lambda row: row['page_title'].replace('_', ' ') in row['content_title'] or 
                                                row['content_title'] in row['page_title'].replace('_', ' '), axis=1)
            logging.info(f"Title match percentage: {df['title_match'].mean()*100:.2f}%")
        
        # Content type classification
        logging.info("== Content Type Classification ==")
        
        def classify_content(content):
            if '[[Category:' in content:
                return 'Category'
            elif 'Volumes' in content or '<lst type=bracket>' in content:
                return 'Bibliography Entry'
            elif re.search(r'\b(essay|essays)\b', content, re.IGNORECASE):
                return 'Essay'
            elif re.search(r'\b(translation|translated by|übersetzt)\b', content, re.IGNORECASE):
                return 'Translation'
            elif re.search(r'\b(review|reviews|reviewed by|rezension)\b', content, re.IGNORECASE):
                return 'Review'
            elif re.search(r'\b(letter|correspondence|brief)\b', content, re.IGNORECASE):
                return 'Correspondence'
            elif re.search(r'\b(film|movie|adaptation)\b', content, re.IGNORECASE):
                return 'Film/Media'
            elif re.search(r'\b(biography|biographie|biografie)\b', content, re.IGNORECASE):
                return 'Biography'
            else:
                return 'Other'
        
        df['content_type'] = df['content'].apply(classify_content)
        logging.info(f"Content type distribution: {df['content_type'].value_counts().to_dict()}")
        
        # Extract bibliographic information
        logging.info("== Bibliographic Information ==")
        
        def extract_biblio_info(content):
            # Year extraction
            year_match = re.search(r'\b(1[8-9]\d{2}|20[0-2]\d)\b', content)
            year = year_match.group(1) if year_match else None
            
            # Publisher extraction with multiple patterns
            publisher_patterns = [
                r'(?:Verlag|Publisher|Press):\s*(.*?)(?:\.|\n|$)',
                r'(?:published by|verlegt bei)\s*(.*?)(?:\.|\n|$)',
                r'\b(?:Verlag|Publishers?)\b[^\n.]*?([\w\s&]+)(?:,|\.|$)'
            ]
            
            publisher = None
            for pattern in publisher_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match and match.group(1):
                    publisher = match.group(1).strip()
                    break
            
            # Location extraction
            common_locations = ['Wien', 'Berlin', 'Frankfurt', 'Leipzig', 'London', 'New York', 
                            'Paris', 'Zürich', 'Hamburg', 'München', 'Salzburg']
            location_pattern = '|'.join(common_locations)
            location_match = re.search(f'\\b({location_pattern})\\b', content)
            location = location_match.group(0) if location_match else None
            
            # Language extraction
            language_match = re.search(r'(?:Language|Sprache):\s*(.*?)(?:\.|\n|$)', content, re.IGNORECASE)
            language = language_match.group(1).strip() if language_match else None
            
            # Page count extraction
            page_match = re.search(r'(\d+)(?:\s*)p\.', content)
            page_count = page_match.group(1) if page_match else None
            
            return {
                'year': year,
                'publisher': publisher,
                'location': location,
                'language': language,
                'page_count': page_count
            }
        
        # Apply to all entries
        biblio_info = df['content'].apply(extract_biblio_info)
        biblio_df = pd.DataFrame(biblio_info.tolist())
        
        # Add extracted info to main dataframe
        df = pd.concat([df, biblio_df], axis=1)
        
        # Log bibliographic info stats
        logging.info(f"Entries with year: {biblio_df['year'].count()} ({biblio_df['year'].count()/len(df)*100:.2f}%)")
        logging.info(f"Entries with publisher: {biblio_df['publisher'].count()} ({biblio_df['publisher'].count()/len(df)*100:.2f}%)")
        logging.info(f"Entries with location: {biblio_df['location'].count()} ({biblio_df['location'].count()/len(df)*100:.2f}%)")
        
        if biblio_df['year'].count() > 0:
            logging.info("Top years:")
            top_years = biblio_df['year'].value_counts().head(10)
            for year, count in top_years.items():
                logging.info(f"  {year}: {count} entries")
        
        if biblio_df['publisher'].count() > 0:
            logging.info("Top publishers:")
            top_publishers = biblio_df['publisher'].value_counts().head(10)
            for publisher, count in top_publishers.items():
                logging.info(f"  {publisher}: {count} entries")
        
        # Generate visualizations if requested
        if generate_plots:
            logging.info("== Generating Visualizations ==")
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Content length distribution
            plt.figure(figsize=(10, 6))
            plt.hist(df['content_length'], bins=50)
            plt.title('Content Length Distribution')
            plt.xlabel('Length (characters)')
            plt.ylabel('Frequency')
            plt.savefig(f'{output_dir}/content_length_distribution.png')
            logging.info("Created content length distribution visualization")
            
            # Content type distribution
            plt.figure(figsize=(12, 6))
            df['content_type'].value_counts().plot(kind='bar')
            plt.title('Content Type Distribution')
            plt.xlabel('Content Type')
            plt.ylabel('Count')
            plt.savefig(f'{output_dir}/content_type_distribution.png')
            logging.info("Created content type distribution visualization")
            
            # Year distribution (if available)
            if 'year' in df.columns and df['year'].count() > 10:
                year_df = df.dropna(subset=['year'])
                year_df['year'] = year_df['year'].astype(int)
                
                plt.figure(figsize=(15, 6))
                year_df['year'].value_counts().sort_index().plot(kind='bar')
                plt.title('Publications by Year')
                plt.xlabel('Year')
                plt.ylabel('Count')
                plt.savefig(f'{output_dir}/year_distribution.png')
                logging.info("Created year distribution visualization")
                
            # Pattern analysis visualization
            plt.figure(figsize=(14, 6))
            pattern_sums = pattern_df.sum().sort_values(ascending=False)
            pattern_sums.plot(kind='bar')
            plt.title('Content Pattern Distribution')
            plt.xlabel('Pattern')
            plt.ylabel('Count')
            plt.tight_layout()
            plt.savefig(f'{output_dir}/pattern_distribution.png')
            logging.info("Created pattern distribution visualization")
        
        # Save enhanced dataset
        enhanced_file = f"zweig_bibliography_enhanced_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(f"{output_dir}/{enhanced_file}", index=False)
        logging.info(f"Saved enhanced dataset to {output_dir}/{enhanced_file}")
        
        return df
        
    except Exception as e:
        logging.error(f"Error analyzing extracted data: {e}")
        raise

def investigate_missing_content():
    """Investigate why we're missing content for many pages"""
    logging.info("== Investigating Missing Content Issue ==")
    
    try:
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get count of pages in the main namespace
        cursor.execute("SELECT COUNT(*) as count FROM zweig_page WHERE page_namespace = 0")
        total_pages = cursor.fetchone()['count']
        logging.info(f"Total pages in main namespace: {total_pages}")
        
        # Analyze BLOB structure
        cursor.execute("SELECT old_id, LENGTH(old_text) as size FROM zweig_text ORDER BY old_id")
        blobs = cursor.fetchall()
        
        logging.info("BLOB structure analysis:")
        for blob in blobs:
            logging.info(f"BLOB {blob['old_id']}: {blob['size']} bytes")
            
            # Get the first few bytes to check the format
            cursor.execute(f"SELECT SUBSTRING(old_text, 1, 1000) as header FROM zweig_text WHERE old_id = {blob['old_id']}")
            header_bytes = cursor.fetchone()['header']
            header = header_bytes.decode('latin1', errors='replace')
            
            # Check what type of content is in this BLOB
            contains_create = 'CREATE TABLE' in header
            contains_insert = 'INSERT INTO' in header
            
            logging.info(f"  Header: {header[:100]}...")
            logging.info(f"  Contains CREATE TABLE: {contains_create}")
            logging.info(f"  Contains INSERT INTO: {contains_insert}")
            
        # Check for multi-value INSERT patterns
        logging.info("Checking for multi-value INSERT statements in BLOBs...")
        
        for blob_id in range(1, 9):
            cursor.execute(f"""
                SELECT SUBSTRING(old_text, 1, 10000) as text_sample 
                FROM zweig_text 
                WHERE old_id = {blob_id}
            """)
            
            sample = cursor.fetchone()['text_sample'].decode('latin1', errors='replace')
            
            # Look for the multi-value INSERT pattern
            multi_pattern = r"INSERT INTO [`\"]zweig_text[`\"] VALUES\s+\([^)]+\),\s*\("
            multi_matches = re.search(multi_pattern, sample)
            
            if multi_matches:
                logging.info(f"  BLOB {blob_id}: Contains multi-value INSERT statements")
                
                # Try to count how many records in the first INSERT
                first_insert = re.search(r"INSERT INTO [`\"]zweig_text[`\"] VALUES\s+(.*?);", sample, re.DOTALL)
                if first_insert:
                    values = first_insert.group(1)
                    record_count = values.count('),(')
                    logging.info(f"    First INSERT statement contains approximately {record_count + 1} records")
                    
                    # Extract an example of a record
                    record_example = re.search(r"\((\d+),\s*_binary '((?:[^'\\]|\\.|'')*?)',\s*_binary '((?:[^'\\]|\\.|'')*?)'\)", values)
                    if record_example:
                        text_id, content, flags = record_example.groups()
                        logging.info(f"    Example record - ID: {text_id}, Flags: {flags}")
                        logging.info(f"    Content preview: {content[:100]}...")
            else:
                logging.info(f"  BLOB {blob_id}: Does not contain multi-value INSERT statements")
                
                # Check for single-value INSERT statements
                single_pattern = r"INSERT INTO [`\"]zweig_text[`\"] VALUES\s+\((\d+),\s*_binary"
                single_match = re.search(single_pattern, sample)
                
                if single_match:
                    logging.info(f"    Contains single-value INSERT statements with ID: {single_match.group(1)}")
                    
                    # Extract an example
                    example = re.search(r"INSERT INTO [`\"]zweig_text[`\"] VALUES\s+\((\d+),\s*_binary '((?:[^'\\]|\\.|'')*?)',\s*_binary '((?:[^'\\]|\\.|'')*?)'\)", sample)
                    if example:
                        text_id, content, flags = example.groups()
                        logging.info(f"    Example record - ID: {text_id}, Flags: {flags}")
                        logging.info(f"    Content preview: {content[:100]}...")
        
        # Test a more robust extraction approach with a direct string search
        logging.info("Testing improved extraction approach...")
        
        # Get a few text IDs to test with
        cursor.execute("""
            SELECT 
                p.page_id, 
                CONVERT(UNHEX(REPLACE(CAST(p.page_title AS CHAR), '0x', '')) USING utf8) AS page_title,
                CAST(c.content_address AS CHAR) as address_str
            FROM zweig_page p
            JOIN zweig_revision r ON p.page_latest = r.rev_id
            JOIN zweig_slots s ON r.rev_id = s.slot_revision_id
            JOIN zweig_content c ON s.slot_content_id = c.content_id
            WHERE p.page_namespace = 0
            ORDER BY RAND()
            LIMIT 5
        """)
        
        test_pages = cursor.fetchall()
        for page in test_pages:
            # Extract text_id from address
            text_id = None
            if 'tt:' in page['address_str']:
                text_id = page['address_str'].split('tt:')[1]
            
            if not text_id:
                continue
                
            logging.info(f"Looking for text_id {text_id} for page {page['page_id']} ({page['page_title']})")
            
            # Search in all BLOBs
            for blob_id in range(1, 9):
                cursor.execute(f"SELECT SUBSTRING(old_text, 1, 100) FROM zweig_text WHERE old_id = {blob_id}")
                if not cursor.fetchone():  # Skip if BLOB doesn't exist
                    continue
                    
                # Use a simple string search first
                cursor.execute(f"""
                    SELECT LOCATE('({text_id},', CONVERT(old_text USING latin1)) as position
                    FROM zweig_text 
                    WHERE old_id = {blob_id}
                """)
                
                position = cursor.fetchone()['position']
                if position > 0:
                    logging.info(f"  Found in BLOB {blob_id} at position {position}")
                    
                    # Get context around the match
                    cursor.execute(f"""
                        SELECT SUBSTRING(CONVERT(old_text USING latin1), {position-10}, 500) as context
                        FROM zweig_text 
                        WHERE old_id = {blob_id}
                    """)
                    
                    context = cursor.fetchone()['context']
                    logging.info(f"  Context: {context[:150]}...")
                    
                    # Try to extract the full record
                    record_match = re.search(r"\("+text_id+r",\s*_binary '((?:[^'\\]|\\.|'')*?)',\s*_binary '((?:[^'\\]|\\.|'')*?)'\)", context)
                    if record_match:
                        content, flags = record_match.groups()
                        logging.info(f"  Successfully extracted content with length {len(content)}")
                        logging.info(f"  Content preview: {content[:100]}...")
                        logging.info(f"  Flags: {flags}")
                    
                    break
                
        # Close database connection
        cursor.close()
        conn.close()
        logging.info("Database connection closed after investigation")
        
    except Exception as e:
        logging.error(f"Error investigating missing content: {e}")
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def extract_sample_data(sample_size=100, output_dir='analysis_output'):
    """Extract a sample of data directly from BLOBs"""
    logging.info(f"== Extracting Sample Data (up to {sample_size} entries) ==")
    
    try:
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)
        
        # Create mapping of page info to text_ids
        cursor.execute("""
            SELECT 
                p.page_id, 
                CONVERT(UNHEX(REPLACE(CAST(p.page_title AS CHAR), '0x', '')) USING utf8) AS page_title,
                c.content_address,
                CAST(c.content_address AS CHAR) as address_str
            FROM zweig_page p
            JOIN zweig_revision r ON p.page_latest = r.rev_id
            JOIN zweig_slots s ON r.rev_id = s.slot_revision_id
            JOIN zweig_content c ON s.slot_content_id = c.content_id
            WHERE p.page_namespace = 0
            ORDER BY RAND()
            LIMIT %s
        """, (sample_size*2,))  # Get more than needed in case some aren't found
        
        pages = cursor.fetchall()
        logging.info(f"Got {len(pages)} random pages to try extracting")
        
        extracted_entries = []
        
        for page in pages:
            if len(extracted_entries) >= sample_size:
                break
                
            # Extract text_id from address
            text_id = None
            if 'tt:' in page['address_str']:
                text_id = page['address_str'].split('tt:')[1]
            elif page['address_str'].startswith('0x'):
                try:
                    hex_bytes = bytes.fromhex(page['address_str'][2:])
                    decoded = hex_bytes.decode('utf-8', errors='replace')
                    if 'tt:' in decoded:
                        text_id = decoded.split('tt:')[1]
                except Exception:
                    pass
            
            if not text_id:
                continue
                
            logging.info(f"Looking for text_id {text_id} for page {page['page_id']} ({page['page_title']})")
            
            # Search in all BLOBs
            for blob_id in range(1, 9):
                # Simple string search first to check if text_id exists in this BLOB
                cursor.execute(f"""
                    SELECT LOCATE('({text_id},', CONVERT(old_text USING latin1)) as position
                    FROM zweig_text 
                    WHERE old_id = {blob_id}
                """)
                
                result = cursor.fetchone()
                if not result:
                    continue
                    
                position = result['position']
                if position > 0:
                    logging.info(f"  Found in BLOB {blob_id} at position {position}")
                    
                    # Get context around the match
                    cursor.execute(f"""
                        SELECT SUBSTRING(CONVERT(old_text USING latin1), {position-10}, 2000) as context
                        FROM zweig_text 
                        WHERE old_id = {blob_id}
                    """)
                    
                    context = cursor.fetchone()['context']
                    
                    # Try to extract the full record
                    record_match = re.search(r"\("+text_id+r",\s*_binary '((?:[^'\\]|\\.|'')*?)',\s*_binary '((?:[^'\\]|\\.|'')*?)'\)", context)
                    if record_match:
                        content, flags = record_match.groups()
                        
                        # Unescape quotes
                        content = content.replace("''", "'")
                        
                        # Create entry
                        entry = {
                            'page_id': page['page_id'],
                            'page_title': page['page_title'],
                            'text_id': text_id,
                            'content': content,
                            'flags': flags,
                            'blob_id': blob_id
                        }
                        
                        extracted_entries.append(entry)
                        logging.info(f"  Extracted entry {len(extracted_entries)}/{sample_size}")
                        break
        
        logging.info(f"Extracted {len(extracted_entries)} entries total")
        
        # Save to CSV
        if extracted_entries:
            os.makedirs(output_dir, exist_ok=True)
            output_file = f"{output_dir}/zweig_sample_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=extracted_entries[0].keys())
                writer.writeheader()
                writer.writerows(extracted_entries)
                
            logging.info(f"Saved sample data to {output_file}")
            
            return extracted_entries
        else:
            logging.warning("No entries were extracted")
            return None
            
    except Exception as e:
        logging.error(f"Error extracting sample data: {e}")
        if 'conn' in locals() and conn.is_connected():
            conn.close()
        return None
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            logging.info("Database connection closed after extraction")

def main():
    """Main function"""
    args = parse_args()
    logging.info("=== BEGINNING ZWEIG BIBLIOGRAPHY DATA ANALYSIS ===")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Extract sample data if requested
    if args.extract:
        sample_data = extract_sample_data(args.sample_size, args.output)
        if sample_data and not args.csv:
            # Use the newly extracted sample for analysis
            args.csv = f"{args.output}/zweig_sample_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    # Analyze extracted data if CSV provided
    if args.csv and os.path.exists(args.csv):
        analyze_extracted_data(args.csv, args.output, not args.no_plots)
    elif args.csv:
        logging.error(f"CSV file not found: {args.csv}")
    
    # Investigate missing content issue
    investigate_missing_content()
    
    logging.info("=== ANALYSIS COMPLETE ===")

if __name__ == "__main__":
    main()