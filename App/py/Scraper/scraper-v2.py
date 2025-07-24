import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote
import re
import math
import pandas as pd
import time

def get_geo_id(location):
    location_encoded = quote(location)
    search_url = f"https://www.linkedin.com/jobs/search?location={location_encoded}"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(search_url, headers=headers, allow_redirects=True)
    m = re.search(r'geoId=(\d+)', resp.url)
    if m:
        return m.group(1)
    m = re.search(r'geoId":(\d+),', resp.text)
    if m:
        return m.group(1)
    raise Exception('Could not extract geoId for location: '+location)

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

'''Life Tip: ChatGPT pe bharosa mat kar

def fetch_job_ids(api_url, num_jobs):
    l = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for i in range(0, math.ceil(num_jobs/25)):
        url = api_url + f"&start={i*25}"
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        alljobs_on_this_page = soup.find_all("li")
        print(f"Found {len(alljobs_on_this_page)} jobs on page {i+1}")
        for jobli in alljobs_on_this_page:
            card = jobli.find("div", {"class": "base-card"})
            if card and card.has_attr('data-entity-urn'):
                jobid = card['data-entity-urn'].split(":")[3]
                l.append(jobid)
        time.sleep(1)  # be nice, avoid getting blocked
    return l'''

def fetch_job_ids(api_url, num_jobs):
    job_ids = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for i in range(0, num_jobs, 25):
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
        k.append(o)
        time.sleep(1)
    return k

# BHIDEGA?
keyword = "Python"
location = "Kannankara"

# GEOID NIKAAALLLLL
geo_id = get_geo_id(location)
print("geoId:", geo_id)


baseapi = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
params = {
    "keywords": keyword,
    "location": location,
#    "geoId": geo_id,
    "geoId": geo_id,
    "trk": "public_jobs_jobs-search-bar_search-submit",
    "start": 0
}
api_url = baseapi + urlencode(params)
print("API url sample:", api_url)

html_search_url = f"https://www.linkedin.com/jobs/search?keywords={quote(keyword)}&location={quote(location)}&geoId={geo_id}"
n_jobs = get_num_jobs(html_search_url)
print("Number of jobs:", n_jobs)

#Do you have a J*b
l = fetch_job_ids(api_url, n_jobs)


k = fetch_job_details(l)

#Pakodee finally ban gye
df = pd.DataFrame(k)
df.to_csv('linkedinjobs.csv', index=False, encoding='utf-8')
print("Job data:", k)
