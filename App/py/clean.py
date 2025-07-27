import pandas as pd
import re
import os

def clean_job_data(csv_file='linkedinjobs.csv', user_params=None):
    """
    Clean and process the LinkedIn jobs CSV data using pandas to remove rows based on user parameters.
    """
    if not os.path.exists(csv_file):
        print(f"CSV file {csv_file} not found!")
        return None

    df = pd.read_csv(csv_file)
    print(f"Original data: {len(df)} rows")

    # Remove dupes and missing data 
    if user_params and user_params.get('remove_duplicates', True):
        df = df.drop_duplicates()
        print(f"After removing duplicates: {len(df)} rows")

    essential_fields = user_params.get('essential_fields', ['company', 'job-title']) if user_params else ['company', 'job-title']
    if essential_fields:
        df = df.dropna(subset=essential_fields)
        print(f"After removing incomplete records: {len(df)} rows")

    # Remove rows based on user-defined filters
    if user_params and 'filters' in user_params:
        for column, condition in user_params['filters'].items():
            if column in df.columns:
                df = df[df[column].str.contains(condition, na=False, regex=True)]
                print(f"After filtering {column} with condition '{condition}': {len(df)} rows")

    # Reset index
    df = df.reset_index(drop=True)

    return df

def save_cleaned_data(df, output_file='linkedinjobs.csv'):
    """
    Save the cleaned data back to CSV
    """
    if df is not None and len(df) > 0:
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Cleaned data saved to {output_file}: {len(df)} jobs")
        
        #Stats 
        print("\n--- Data Summary ---")
        print(f"Total jobs: {len(df)}")
        print(f"Unique companies: {df['company'].nunique()}")
        print(f"Unique locations: {df['location'].nunique()}")
        print("\nJob types distribution:")
        print(df['job_type'].value_counts())
        print("\nExperience levels distribution:")
        print(df['level'].value_counts())
        
        return True
    else:
        print("No data to save!")
        return False

def validate_data(df):
    """
    Validate the cleaned data for quality issues
    """
    if df is None or len(df) == 0:
        print("No data to validate!")
        return False
    
    print("\n--- Data Validation ---")

    missing_company = df['company'].isna().sum()
    missing_title = df['job-title'].isna().sum()
    missing_link = df['link'].isna().sum()
    
    print(f"Missing company names: {missing_company}")
    print(f"Missing job titles: {missing_title}")
    print(f"Missing job links: {missing_link}")
    
    # Check URL format
    invalid_urls = len(df[~df['link'].str.contains('linkedin.com/jobs/view/', na=False)])
    print(f"Invalid LinkedIn URLs: {invalid_urls}")
    
    return True

def filter_by_criteria(df, user_criteria):
    """
    Filter jobs based on user's search criteria to only show relevant options
    """
    if df is None or len(df) == 0:
        return df
    
    # I died here :-(
    print(f"\n--- Filtering by User Criteria ---")
    print(f"Original jobs: {len(df)}")
    
    filtered_df = df.copy()
    
    #Filter by location
    if user_criteria.get('location'):
        search_location = user_criteria['location'].lower().strip()
        print(f"🎯 STRICT LOCATION FILTERING for: {search_location}")
        

        print("Available job locations in data:")
        for loc in filtered_df['location'].unique():
            print(f"  - {loc}")
        
        search_city = search_location
        if ',' in search_location:
            search_city = search_location.split(',')[0].strip()
        
        #Common City Names
        city_variations = {
            'bangalore': ['bangalore', 'bengaluru'],
            'bengaluru': ['bangalore', 'bengaluru'],
            'mumbai': ['mumbai', 'bombay'],
            'bombay': ['mumbai', 'bombay'],
            'delhi': ['delhi', 'new delhi'],
            'new delhi': ['delhi', 'new delhi'],
            'pune': ['pune', 'poona'],
            'chennai': ['chennai', 'madras'],
            'kolkata': ['kolkata', 'calcutta']
        }
        
        search_variations = city_variations.get(search_city, [search_city])
        
        location_patterns = []
        for variation in search_variations:
            location_patterns.append(variation)
        
        print(f"Searching for city variations: {location_patterns}")
        
        #Remote Jobs
        remote_mask = filtered_df['location'].str.lower().str.contains('remote|work from home|wfh|anywhere', na=False, regex=True)
        
        location_mask = pd.Series([False] * len(filtered_df))
        for pattern in location_patterns:
            location_mask |= filtered_df['location'].str.lower().str.contains(pattern, na=False, regex=False)
        
        print(f"Remote jobs found: {remote_mask.sum()}")
        print(f"Jobs matching location '{search_location}': {location_mask.sum()}")
        
        final_mask = remote_mask | location_mask
        
        if final_mask.sum() == 0:
            print(f"NO JOBS FOUND IN {search_location.upper()}!")
            print("NO REMOTE JOBS FOUND!")
            print("REMOVING ALL JOBS FROM CSV!")
            #Dataset to be cleared completely
            filtered_df = pd.DataFrame(columns=filtered_df.columns)
        else:
            # Apply strict filter - remove all jobs that don't match
            filtered_df = filtered_df[final_mask]
            print(f"STRICT FILTER APPLIED: Kept {len(filtered_df)} jobs (out of original {len(df)})")
            print(f"   - Remote jobs: {remote_mask.sum()}")
            print(f"   - Jobs in {search_location}: {location_mask.sum()}")
    
    # Filter by remote preference (if specified)
    if user_criteria.get('remoteOnly') and len(filtered_df) > 0:
        remote_jobs = filtered_df[
            filtered_df['location'].str.lower().str.contains('remote|work from home|wfh|anywhere', na=False, regex=True)
        ]
        if len(remote_jobs) > 0:
            filtered_df = remote_jobs
            print(f"After remote-only filter: {len(filtered_df)} jobs")
        else:
            print("❌ NO REMOTE JOBS FOUND! User wanted remote only - removing all jobs!")
            filtered_df = pd.DataFrame(columns=filtered_df.columns)
    
    # Filter by job type (If specified)
    if user_criteria.get('jobType') and user_criteria['jobType'] != 'any':
        job_type = user_criteria['jobType'].lower()
        if job_type == 'internship':
            filtered_df = filtered_df[
                filtered_df['job_type'].str.lower().str.contains('internship|intern', na=False) |
                filtered_df['job-title'].str.lower().str.contains('intern', na=False) |
                filtered_df['level'].str.lower().str.contains('internship', na=False)
            ]
        elif job_type == 'full-time':
            filtered_df = filtered_df[
                filtered_df['job_type'].str.lower().str.contains('full', na=False)
            ]
        elif job_type == 'part-time':
            filtered_df = filtered_df[
                filtered_df['job_type'].str.lower().str.contains('part', na=False)
            ]
        elif job_type == 'contract':
            filtered_df = filtered_df[
                filtered_df['job_type'].str.lower().str.contains('contract', na=False)
            ]
        print(f"After job type filter ({job_type}): {len(filtered_df)} jobs")
    
    # Filter by experience level (if specified)
    if user_criteria.get('experienceLevel') and user_criteria['experienceLevel'] != 'any':
        exp_level = user_criteria['experienceLevel'].lower()
        if exp_level in ['entry', 'entry level', 'junior']:
            filtered_df = filtered_df[
                filtered_df['level'].str.lower().str.contains('entry|junior|intern', na=False)
            ]
        elif exp_level in ['mid', 'mid-senior', 'senior']:
            filtered_df = filtered_df[
                filtered_df['level'].str.lower().str.contains('mid|senior', na=False)
            ]
        elif exp_level in ['executive', 'director']:
            filtered_df = filtered_df[
                filtered_df['level'].str.lower().str.contains('executive|director', na=False)
            ]
        print(f"After experience level filter ({exp_level}): {len(filtered_df)} jobs")
    
    # Filter by skillz
    if user_criteria.get('skills'):
        skills = user_criteria['skills'].lower().split()
        skill_pattern = '|'.join(skills)
        filtered_df = filtered_df[
            filtered_df['job-title'].str.lower().str.contains(skill_pattern, na=False) |
            filtered_df['company'].str.lower().str.contains(skill_pattern, na=False)
        ]
        print(f"After skills filter ({user_criteria['skills']}): {len(filtered_df)} jobs")
    
    # Filter by job title (If Specified)
    if user_criteria.get('jobTitle') and user_criteria['jobTitle'].strip():
        job_title_keywords = user_criteria['jobTitle'].lower().split()
        title_pattern = '|'.join(job_title_keywords)
        filtered_df = filtered_df[
            filtered_df['job-title'].str.lower().str.contains(title_pattern, na=False)
        ]
        print(f"After job title filter ({user_criteria['jobTitle']}): {len(filtered_df)} jobs")
    
    print(f"Final filtered jobs: {len(filtered_df)}")
    
    return filtered_df

def smart_clean_and_filter(user_criteria=None, csv_file='linkedinjobs.csv'):
    #Epic filteration code and cleaning
    print("Cleaning and filtering data...")
    
    cleaned_df = clean_job_data(csv_file)
    
    if cleaned_df is None or len(cleaned_df) == 0:
        print("No data to clean")
        return None
    
    if user_criteria:
        print(f"Applying user criteria: {user_criteria}")
        filtered_df = filter_by_criteria(cleaned_df, user_criteria)
    else:
        print("No user criteria provided, keeping all cleaned jobs")
        filtered_df = cleaned_df
    
    # Step 3: Final quality check
    if len(filtered_df) == 0:
        print("NO JOBS FOUND MATCHING USER'S LOCATION CRITERIA")
        if user_criteria and user_criteria.get('location'):
            print(f"NO JOBS IN '{user_criteria['location'].upper()}' OR REMOTE POSITIONS!")
        print("CSV TO BE CLEANED")
    
    # Step 4: Validate and save
    validate_data(filtered_df)
    
    if save_cleaned_data(filtered_df, csv_file):
        print(f"\nCleaning completed! {len(filtered_df)} relevant jobs found")
        return filtered_df
    else:
        print("Failed to save cleaned data!")
        return None

def main():
#This is the main thingy
    print("Starting LinkedIn jobs data cleaning process...")
    
    # Clean the data (basic cleaning without criteria)
    cleaned_df = clean_job_data()
    
    if cleaned_df is not None:
        # Validate the cleaned data
        validate_data(cleaned_df)
        
        # Save the cleaned data
        if save_cleaned_data(cleaned_df):
            print("\nData cleaning completed successfully!")
        else:
            print("Failed to save cleaned data!")
    else:
        print("Data cleaning failed!")

if __name__ == "__main__":
    main()
