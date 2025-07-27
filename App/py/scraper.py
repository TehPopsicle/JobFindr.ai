
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import re
import math
import pandas as pd
import time

def get_num_jobs(url):
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}
    res = requests.get(url, headers=headers)
    m = re.search(r'([\d,]+) jobs', res.text)
    if m:
        num = m.group(1).replace(',','')
        return int(num)
    soup = BeautifulSoup(res.text,'html.parser')
    h1 = soup.find('h1')
    if h1 and h1.text:
        m = re.search(r'([\d,]+) jobs', h1.text)
        if m:
            return int(m.group(1).replace(',',''))
    return 25*4 

def fetch_job_ids(api_url, num_jobs):
    job_ids = []
    headers = {"User-Agent": "Mozilla/5.0"}
    max_jobs = min(num_jobs, 100)  # Limit to prevent overload
    
    for i in range(0, max_jobs, 25):
        page_url = api_url + f"&start={i}"
        res = requests.get(page_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        alljobs_on_this_page = soup.find_all("li")
        
        for jobli in alljobs_on_this_page:
            card = jobli.find("div", {"class": "base-card"})
            if card and card.has_attr('data-entity-urn'):
                jobid = card['data-entity-urn'].split(":")[3]
                job_ids.append(jobid)
        time.sleep(1)
    return job_ids

def fetch_job_details(job_ids):
    jobs = []
    headers = {"User-Agent": "Mozilla/5.0"}
    target_url = 'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}'
    
    for job_id in job_ids:
        try:
            resp = requests.get(target_url.format(job_id), headers=headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            job = {}
            
            try:
                job["company"] = soup.find("div", {"class": "top-card-layout__card"}).find("a").find("img").get('alt')
            except:
                job["company"] = None

            try:
                job["job-title"] = soup.find("div", {"class": "top-card-layout__entity-info"}).find("a").text.strip()
            except:
                job["job-title"] = None

            try:
                job["level"] = soup.find("ul", {"class": "description__job-criteria-list"}).find("li").text.replace("Seniority level", "").strip()
            except:
                job["level"] = None
                
            try:
                location_elem = soup.find("span", {"class": "topcard__flavor topcard__flavor--bullet"})
                job["location"] = location_elem.text.strip() if location_elem else None
            except:
                job["location"] = None
                
            try:
                job_type_items = soup.find("ul", {"class": "description__job-criteria-list"}).find_all("li")
                for item in job_type_items:
                    if "Employment type" in item.text:
                        job["job_type"] = item.text.replace("Employment type", "").strip()
                        break
                else:
                    job["job_type"] = None
            except:
                job["job_type"] = None
                
            job["link"] = f"https://www.linkedin.com/jobs/view/{job_id}"
            jobs.append(job)
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching job {job_id}: {e}")
            continue
    
    return jobs

def search_jobs(keywords="", location="", geo_id="", job_title=""):
    """Main function to search for jobs"""
    try:
        # Combine keywords and job_title
        search_keywords = f"{keywords} {job_title}".strip()
        
        # Build API URL
        api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={quote(search_keywords)}&location={quote(location)}&geoId={geo_id}"
        
        # Build HTML search URL to get job count
        html_search_url = f"https://www.linkedin.com/jobs/search?keywords={quote(search_keywords)}&location={quote(location)}&geoId={geo_id}"
        
        # Get number of jobs
        n_jobs = get_num_jobs(html_search_url)
        print(f"Found {n_jobs} jobs for '{search_keywords}' in {location}")
        
        # Fetch job IDs
        job_ids = fetch_job_ids(api_url, n_jobs)
        print(f"Collected {len(job_ids)} job IDs")
        
        # Fetch job details
        jobs = fetch_job_details(job_ids)
        print(f"Successfully scraped {len(jobs)} jobs")
        
        return jobs
        
    except Exception as e:
        print(f"Error in search_jobs: {e}")
        return []

def extract_job_type(description_text):
    """Extract job type from job description"""
    if not description_text:
        return None
    
    text_lower = description_text.lower()
    
    if 'full-time' in text_lower or 'full time' in text_lower:
        return 'Full Time'
    elif 'part-time' in text_lower or 'part time' in text_lower:
        return 'Part Time'
    elif 'contract' in text_lower:
        return 'Contract'
    elif 'internship' in text_lower or 'intern' in text_lower:
        return 'Internship'
    elif 'temporary' in text_lower or 'temp' in text_lower:
        return 'Temporary'
    
    return 'Full Time'  # Default

def fetch_job_details(jobids):
    k = []
    headers = {"User-Agent": "Mozilla/5.0"}
    target_url = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
    
    for jid in jobids:
        o = {}
        resp = requests.get(target_url.format(jid), headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        try:
            o["company"] = soup.find("div",{"class":"top-card-layout__card"}).find("a").find("img").get('alt')
        except:
            o["company"] = None
            
        try:
            o["job-title"] = soup.find("div",{"class":"top-card-layout__entity-info"}).find("a").text.strip()
        except:
            o["job-title"] = None
            
        try:
            o["level"] = soup.find("ul",{"class":"description__job-criteria-list"}).find("li").text.replace("Seniority level","").strip()
        except:
            o["level"] = None
            
        # Extract job location
        try:
            location_elem = soup.find("span", {"class": "topcard__flavor--bullet"})
            if location_elem:
                o["location"] = location_elem.text.strip()
            else:
                # Alternative location extraction
                location_elem = soup.find("div", {"class": "top-card-layout__entity-info"})
                if location_elem:
                    spans = location_elem.find_all("span")
                    for span in spans:
                        if span.text and (',' in span.text or 'Remote' in span.text):
                            o["location"] = span.text.strip()
                            break
        except:
            o["location"] = None
            
        # Extract job link
        try:
            o["link"] = f"https://www.linkedin.com/jobs/view/{jid}"
        except:
            o["link"] = None
            
        # Extract job type from description
        try:
            description = soup.find("div", {"class": "description__text"})
            if description:
                desc_text = description.get_text()
                o["job_type"] = extract_job_type(desc_text)
            else:
                o["job_type"] = None
        except:
            o["job_type"] = None
            
        # Extract employment type from criteria list
        try:
            criteria_list = soup.find("ul", {"class": "description__job-criteria-list"})
            if criteria_list:
                criteria_items = criteria_list.find_all("li")
                for item in criteria_items:
                    text = item.get_text().lower()
                    if 'employment type' in text:
                        emp_type = text.replace('employment type', '').strip()
                        if emp_type:
                            o["job_type"] = emp_type.title()
                        break
        except:
            pass
            
        k.append(o)
        time.sleep(1)  # Be respectful to LinkedIn's servers
        
    return k

def search_jobs(keywords, location, geo_id, job_title="", user_criteria=None):
    """Main function to search for jobs"""
    
    # Combine keywords and job title for search
    search_terms = []
    if job_title:
        search_terms.append(job_title)
    if keywords:
        search_terms.append(keywords)
    
    combined_keywords = " ".join(search_terms)
    
    baseapi = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
    params = {
        "keywords": combined_keywords,
        "location": location,
        "geoId": geo_id,
        "trk": "public_jobs_jobs-search-bar_search-submit",
        "start": 0
    }
    api_url = baseapi + urlencode(params)
    
    html_search_url = f"https://www.linkedin.com/jobs/search?keywords={quote(combined_keywords)}&location={quote(location)}&geoId={geo_id}"
    n_jobs = get_num_jobs(html_search_url)
    
    print(f"Found {n_jobs} jobs for search: {combined_keywords} in {location}")
    
    job_ids = fetch_job_ids(api_url, n_jobs)
    print(f"Fetched {len(job_ids)} job IDs")
    
    if not job_ids:
        return []
    
    jobs = fetch_job_details(job_ids)
    
    # Save raw scraped data to CSV
    df = pd.DataFrame(jobs)
    df.to_csv('linkedinjobs.csv', index=False, encoding='utf-8')
    print(f"Raw data saved to CSV: {len(jobs)} jobs")
    
    print("ℹ️ Scraper completed. Data saved to linkedinjobs.csv")
    print("ℹ️ Next step: Run clean.py to filter and clean the data")
    
    return jobs

if __name__ == "__main__":
    # Test the scraper
    from geoid import get_geo_id
    
    keyword = "Python Developer"
    location = "Delhi"
    geo_id = get_geo_id(location)
    
    if geo_id:
        jobs = search_jobs(keyword, location, geo_id)
        print(f"Found {len(jobs)} jobs")
        for job in jobs[:3]:  # Print first 3 jobs
            print(f"Title: {job.get('job-title')}")
            print(f"Company: {job.get('company')}")
            print(f"Location: {job.get('location')}")
            print(f"Type: {job.get('job_type')}")
            print(f"Link: {job.get('link')}")
            print("---")
    else:
        print("Could not get geo_id for location")
