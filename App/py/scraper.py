import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import re
import time
import pandas as pd

def get_num_jobs(search_url):
    headers = {"User-Agent":"Mozilla/5.0"}
    res = requests.get(search_url, headers=headers)
    # Try to find count via regex
    m = re.search(r'([\d,]+) jobs', res.text)
    if m:
        return int(m.group(1).replace(',',''))
    soup = BeautifulSoup(res.text, 'html.parser')
    h1 = soup.find('h1')
    if h1 and h1.text:
        m = re.search(r'([\d,]+) jobs', h1.text)
        if m:
            return int(m.group(1).replace(',', ''))
    # Default fallback
    return 25*4

def fetch_job_ids(api_url, num_jobs):
    job_ids = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for i in range(0, num_jobs, 25):
        page_url = f"{api_url}&start={i}"
        res = requests.get(page_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        for jobli in soup.find_all("li"):
            card = jobli.find("div", {"class": "base-card"})
            if card and card.has_attr('data-entity-urn'):
                jobid = card['data-entity-urn'].split(":")[3]
                job_ids.append(jobid)
        time.sleep(1)
    return job_ids

def fetch_job_details(job_ids):
    results = []
    headers = {"User-Agent": "Mozilla/5.0"}
    api_template = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"

    for jid in job_ids:
        data = {}
        url = api_template.format(jid)
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Job Title
        try:
            data["job_title"] = soup.find("h1", class_="top-card-layout__title").get_text(strip=True)
        except:
            data["job_title"] = None

        # Company Name
        try:
            data["company"] = soup.find("a", {"class":"topcard__org-name-link"}).get_text(strip=True)
        except:
            try:
                data["company"] = soup.find("span", {"class":"topcard__flavor"}).get_text(strip=True)
            except:
                data["company"] = None

        # Location
        try:
            data["location"] = soup.find("span", class_="topcard__flavor topcard__flavor--bullet").get_text(strip=True)
        except:
            data["location"] = None

        # Job Link
        data["job_link"] = f"https://www.linkedin.com/jobs/view/{jid}/"

        # Job Type and Skills
        data["job_type"] = None
        data["skills"] = []

        try:
            criteria = soup.find("ul", {"class":"description__job-criteria-list"}).find_all("li")
            for li in criteria:
                header = li.find("h3")
                if header:
                    label = header.text.strip()
                    value = li.find("span").text.strip()
                    if "Employment type" in label:
                        data["job_type"] = value
                    if "Skills" in label or "Seniority level" in label:
                        spans = li.find_all("span")[1:]  # skip the label span
                        skills = [span.text.strip() for span in spans if span.text.strip()]
                        data["skills"].extend(skills)
        except:
            pass

        results.append(data)
        time.sleep(1)
    return results

if __name__ == "__main__":
    # Customizable parameters
    keyword = "Python"
    location = "Delhi"
    geo_id = 226279558

    # Optionally customize more params for experimentation
    params = {
        "keywords": keyword,
        "location": location,
        "geoId": geo_id,
        "trk": "public_jobs_jobs-search-bar_search-submit",
        "start": 0
    }

    baseapi = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
    api_url = baseapi + urlencode(params)
    print("[i] Using LinkedIn Jobs API URL:", api_url)

    html_search_url = f"https://www.linkedin.com/jobs/search?keywords={quote(keyword)}&location={quote(location)}&geoId={geo_id}"

    num_jobs = get_num_jobs(html_search_url)
    print("[i] Number of jobs found:", num_jobs)

    job_ids = fetch_job_ids(api_url, num_jobs)
    print(f"[i] Fetched {len(job_ids)} job IDs")

    job_data = fetch_job_details(job_ids)
    print(f"[i] Scraped {len(job_data)} job details")

    # Export to CSV
    df = pd.DataFrame(job_data)
    df.to_csv('linkedinjobs_full.csv', index=False, encoding='utf-8')
    print("[i] Exported data to linkedinjobs_full.csv")
