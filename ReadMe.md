# Klawiter-Rescue: Stefan Zweig Bibliography Database Recovery

This project preserves and analyzes the Klawiter database, a comprehensive bibliography of Stefan Zweig's works compiled by Dr. Randolph J. Klawiter of Notre Dame University. The database was originally hosted on a MediaWiki platform that has been discontinued.

## Purpose

This repository contains tools to extract, process, and analyze bibliographic data from the complex MediaWiki database structure. The project aims to rescue valuable scholarly data that would otherwise be lost due to institutional transitions.

## Repository Structure

- **process-wiki.py**: Initial script for importing raw BLOB data into MySQL
- **extract-klawiter-data-from-db.py**: Main extraction script for bibliography data
- **analyse-csv-output.py**: Analysis script for the extracted CSV data
- **analyse-zweig-data.py**: Additional analysis tools for the bibliography
- **SQL-DB-KNOWLEDGE.md**: Documentation of the database structure
- **CLAUDE.md**: Documentation of the extraction system
- **CLAUDE-CSV-ANALYSE.md**: Documentation of the CSV analysis approach
- **bibliography_analysis/**: Output directory for visualizations and analysis results

## Setup

1. Create a MySQL database for the Klawiter data
2. Configure your database settings:
   ```python
   DB_CONFIG = {
       'host': 'localhost',
       'user': 'root',
       'password': 'your_password',
       'database': 'klawiter'
   }
   ```
3. Install required Python packages:
   ```
   pip install pandas matplotlib seaborn numpy mysql-connector-python
   ```

## Script Descriptions

- **process-wiki.py**: Imports raw binary files (zt_00 to zt_07) into the MySQL database as BLOBs
- **extract-klawiter-data-from-db.py**: Extracts bibliographic content from BLOBs using string search and regex
- **analyse-csv-output.py**: Analyzes extracted data with visualizations for content types, language distribution, etc.

## Usage

1. Import the raw data:
   ```
   python process-wiki.py
   ```

2. Extract bibliography data:
   ```
   python extract-klawiter-data-from-db.py --extract
   ```

3. Analyze the extracted data:
   ```
   python analyse-csv-output.py
   ```

## Output

The analysis generates:
- CSV files containing the extracted bibliography data
- Visualizations in the bibliography_analysis directory
- A comprehensive log file with detailed statistics
- An HTML report summarizing the analysis

## Technical Background

The Klawiter database uses a complex multi-layered structure:
1. MediaWiki tables (zweig_page, zweig_revision, zweig_slots, zweig_content)
2. SQL dump files as BLOBs in the zweig_text.old_text column
3. INSERT statements within these BLOBs
4. Actual bibliography content embedded within INSERT statements