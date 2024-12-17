# JapanCompanyFilter

An automated tool to filter Japanese companies based on their review scores from OpenWork and En-Tenshoku (エン転職), with the ability to automatically fetch company lists from Green Japan.

## Overview
This tool has two main functions:
1. Automatic company list extraction from Green Japan
2. Company filtering based on review scores from OpenWork and En-Tenshoku

## Key Features
### Green Japan List Extraction
- Automatically extracts company names from Green Japan search results
- Saves extracted company lists automatically
- Supports automatic scrolling through multiple pages

### Company Filtering
- Automatic retrieval of OpenWork overall ratings
- Automatic retrieval of En-Tenshoku review scores
- Company filtering based on specified score thresholds
- Automatic saving of filtered results

## How to Use
### Step 1: Get Company List from Green Japan
1. Launch the application
2. Click "Start Green Japan Search"
3. Green Japan search page will open
4. Set your desired search criteria
5. Click "Start Scraping"
6. Company list will be automatically saved

### Step 2: Filter Companies
1. Click "Select File" and choose the file saved from Step 1 (or any existing company list)
2. Enter minimum OpenWork score (e.g., 3.5)
3. Enter minimum En-Tenshoku score (e.g., 3.5)
4. Click "Start Filtering"
5. Results will be automatically saved when processing is complete

## Output
- Green Japan results: Saved as "company_names.txt"
- Filtering results: Saved as "[original_filename]_FilteredbyOpenworkAndEngage.txt"

## Requirements
- Internet connection
- Chrome browser installed
- Search criteria on Green Japan must be set manually
- Processing large lists of companies may take some time

## About the Developer
This tool was developed to streamline the job hunting process in Japan by automatically filtering companies based on employee satisfaction ratings.

**Developer:** Sinuo Hao  
**Contact:** sinuohao514@gmail.com

I am currently job hunting in Japan and created this tool to help identify companies with good employee satisfaction ratings. I hope this tool can help others in their job search as well.

## License
This tool is free to use.
