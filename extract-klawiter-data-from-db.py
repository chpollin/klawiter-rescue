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
    'database': ''
}

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Extract and analyze Stefan Zweig bibliography data')
    parser.add_argument('--csv', default=None, help='Path to CSV file with extracted data')
    parser.add_argument('--extract', action='store_true', help='Extract data directly from BLOBs')
    parser.add_argument('--sample-size', type=int, default=100, help='Number of entries to extract (use 0 for all entries)')
    parser.add_argument('--output', default='analysis_output', help='Output directory for extraction and analysis results')
    parser.add_argument('--no-plots', action='store_true', help='Skip generating plots')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze existing data, skip extraction')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of pages to process')
    parser.add_argument('--blob-id', type=int, default=None, help='Process only specific BLOB ID')
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
            # Fix: Handle NaN values in page_title
            df['title_match'] = df.apply(lambda row: 
                                    False if pd.isna(row['page_title']) else 
                                    str(row['page_title']).replace('_', ' ') in row['content_title'] or 
                                    row['content_title'] in str(row['page_title']).replace('_', ' '), 
                                    axis=1)
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
            
            # BLOB distribution if available
            if 'blob_id' in df.columns:
                plt.figure(figsize=(10, 6))
                df['blob_id'].value_counts().sort_index().plot(kind='bar')
                plt.title('Content Distribution by BLOB')
                plt.xlabel('BLOB ID')
                plt.ylabel('Number of Entries')
                plt.savefig(f'{output_dir}/blob_distribution.png')
                logging.info("Created BLOB distribution visualization")
        
        # Save enhanced dataset
        enhanced_file = f"zweig_bibliography_enhanced_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(f"{output_dir}/{enhanced_file}", index=False)
        logging.info(f"Saved enhanced dataset to {output_dir}/{enhanced_file}")
        
        return df
        
    except Exception as e:
        logging.error(f"Error analyzing extracted data: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None

def extract_content_from_blobs(sample_size=0, output_dir='extraction_output', limit=None, specific_blob=None):
    """Extract content directly from BLOBs using optimized string search"""
    if sample_size == 0:
        logging.info("== Extracting ALL Data from BLOBs ==")
    else:
        logging.info(f"== Extracting Sample Data (up to {sample_size} entries) ==")
    
    try:
        conn = connect_to_db()
        cursor = conn.cursor(dictionary=True)
        
        # Create mapping of page info to text_ids
        query = """
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
        """
        
        # Apply limit if provided
        if sample_size > 0:
            # Get more pages than needed in case some aren't found
            query += f" ORDER BY RAND() LIMIT {sample_size * 2}"
        elif limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        pages = cursor.fetchall()
        total_pages = len(pages)
        logging.info(f"Got {total_pages} pages to extract")
        
        # Track progress
        start_time = datetime.now()
        extracted_entries = []
        not_found_pages = []
        
        # Prepare blob processing
        if specific_blob:
            blob_ids = [specific_blob]
            logging.info(f"Processing only BLOB {specific_blob}")
        else:
            cursor.execute("SELECT old_id FROM zweig_text ORDER BY old_id")
            blob_ids = [row['old_id'] for row in cursor.fetchall()]
            logging.info(f"Processing {len(blob_ids)} BLOBs")
        
        # Count entries per BLOB for statistics
        blob_counts = {blob_id: 0 for blob_id in blob_ids}
        
        # Process in batches to save memory
        batch_size = 500
        for i in range(0, len(pages), batch_size):
            batch = pages[i:i+batch_size]
            logging.info(f"Processing batch {i//batch_size + 1}/{(len(pages) + batch_size - 1)//batch_size} ({len(batch)} pages)")
            
            # Process each page in batch
            for page_idx, page in enumerate(batch):
                # Progress reporting
                if page_idx % 50 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    pages_per_second = (i + page_idx) / elapsed if elapsed > 0 else 0
                    logging.info(f"Progress: {i + page_idx}/{total_pages} pages, {len(extracted_entries)} entries found ({pages_per_second:.2f} pages/sec)")
                
                # Check if we've extracted enough entries
                if sample_size > 0 and len(extracted_entries) >= sample_size:
                    logging.info(f"Reached target of {sample_size} entries, stopping extraction")
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
                    
                # Search in all BLOBs
                found = False
                for blob_id in blob_ids:
                    # Skip already checked BLOBs
                    if blob_id in page.get('checked_blobs', []):
                        continue
                        
                    # Simple string search to check if text_id exists in this BLOB
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
                            blob_counts[blob_id] += 1
                            found = True
                            
                            # Log every 100 entries
                            if len(extracted_entries) % 100 == 0:
                                logging.info(f"Extracted {len(extracted_entries)} entries so far")
                            break
                
                # Track pages where content was not found
                if not found:
                    not_found_pages.append(page)
                    
                # Stop if we've reached the sample size
                if sample_size > 0 and len(extracted_entries) >= sample_size:
                    break
            
            # Stop batch processing if we've reached the sample size
            if sample_size > 0 and len(extracted_entries) >= sample_size:
                break
                
            # Save progress after each batch
            if extracted_entries:
                os.makedirs(output_dir, exist_ok=True)
                batch_output_file = f"{output_dir}/zweig_extraction_progress_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                
                with open(batch_output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=extracted_entries[0].keys())
                    writer.writeheader()
                    writer.writerows(extracted_entries)
                
                logging.info(f"Saved batch progress to {batch_output_file}")
        
        # Final statistics
        elapsed = (datetime.now() - start_time).total_seconds()
        extraction_rate = len(extracted_entries) / elapsed if elapsed > 0 else 0
        
        logging.info(f"Extraction complete: {len(extracted_entries)} entries extracted in {elapsed:.2f} seconds ({extraction_rate:.2f} entries/sec)")
        
        # Log BLOB statistics
        logging.info("Entries found per BLOB:")
        for blob_id, count in blob_counts.items():
            logging.info(f"  BLOB {blob_id}: {count} entries")
        
        # Log not found pages
        logging.info(f"Content not found for {len(not_found_pages)} pages")
        
        # Save final results
        if extracted_entries:
            os.makedirs(output_dir, exist_ok=True)
            output_file = f"{output_dir}/zweig_extraction_complete_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=extracted_entries[0].keys())
                writer.writeheader()
                writer.writerows(extracted_entries)
            
            logging.info(f"Saved complete extraction to {output_file}")
            
            return output_file, extracted_entries
        else:
            logging.warning("No entries were extracted")
            return None, None
            
    except Exception as e:
        logging.error(f"Error extracting data: {e}")
        import traceback
        logging.error(traceback.format_exc())
        if 'conn' in locals() and conn.is_connected():
            conn.close()
        return None, None
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            logging.info("Database connection closed after extraction")

def main():
    """Main function"""
    args = parse_args()
    logging.info("=== BEGINNING STEFAN ZWEIG BIBLIOGRAPHY EXTRACTION AND ANALYSIS ===")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Extract data if requested
    extraction_file = None
    extracted_data = None
    
    if args.extract and not args.analyze_only:
        logging.info("Starting data extraction...")
        extraction_file, extracted_data = extract_content_from_blobs(
            sample_size=args.sample_size, 
            output_dir=args.output,
            limit=args.limit,
            specific_blob=args.blob_id
        )
    
    # Analyze data (either from extraction or from provided CSV)
    csv_to_analyze = extraction_file or args.csv
    
    if csv_to_analyze and os.path.exists(csv_to_analyze):
        logging.info(f"Analyzing data from {csv_to_analyze}...")
        analyze_extracted_data(csv_to_analyze, args.output, not args.no_plots)
    elif csv_to_analyze:
        logging.error(f"CSV file not found: {csv_to_analyze}")
    
    logging.info("=== EXTRACTION AND ANALYSIS COMPLETE ===")

if __name__ == "__main__":
    main()