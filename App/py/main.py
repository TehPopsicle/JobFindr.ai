

from flask import Flask, request, jsonify, render_template_string, send_from_directory
import json
import requests
import os
from scraper import search_jobs
from clean import smart_clean_and_filter
from geoid import get_geo_id
import dotenv
from together import Together


dotenv.load_dotenv(dotenv_path='./../.env')
print("API KEY:", os.getenv('TOGETHER_API_KEY'))
client = Together(api_key=os.getenv('TOGETHER_API_KEY'))

app = Flask(__name__, static_folder='..', static_url_path='')

# Together AI API configuration
TOGETHER_API_KEY = os.environ.get('TOGETHER_API_KEY')
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"

def analyze_job_with_ai(job, user_criteria):
    """Use Together AI to analyze job fit"""
    if not TOGETHER_API_KEY:
        return {"score": 0, "analysis": "N/A"}
    
    prompt = f"""
    Analyze how well this job matches the user's criteria and provide a score from 1-10 and brief analysis.
    
    Job Details:
    - Title: {job.get('job-title', 'N/A')}
    - Company: {job.get('company', 'N/A')}
    - Level: {job.get('level', 'N/A')}
    - Location: {job.get('location', 'N/A')}
    - Type: {job.get('job_type', 'N/A')}
    
    User Criteria:
    - Skills: {user_criteria.get('skills', 'N/A')}
    - Job Title: {user_criteria.get('jobTitle', 'Any')}
    - Experience Level: {user_criteria.get('experienceLevel', 'Any')}
    - Job Type: {user_criteria.get('jobType', 'Any')}
    - Remote Only: {user_criteria.get('remoteOnly', False)}
    
    Respond in JSON format: {{"score": number, "analysis": "brief explanation"}}
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        response = requests.post(TOGETHER_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Try to parse JSON from response
            try:
                ai_result = json.loads(content)
                return ai_result
            except:
                # Fallback if JSON parsing fails
                return {"score": 0, "analysis": content[:100] + "..."}
        else:
            return {"score": 0, "analysis": "AI analysis failed - showing job anyway"}
            
    except Exception as e:
        return {"score": 0, "analysis": f"AI error - showing job anyway: {str(e)[:50]}..."}

def filter_jobs(jobs, criteria):
    """Filter jobs based on user criteria"""
    filtered = []
    
    print(f"Starting with {len(jobs)} jobs")
    
    for job in jobs:
        # Skip jobs with missing essential data
        if not job.get('job-title') or not job.get('company'):
            continue
            
        # Basic filtering (more lenient)
        if criteria.get('jobType') and job.get('job_type'):
            if criteria['jobType'].lower() not in job['job_type'].lower():
                continue
                
        if criteria.get('experienceLevel') and job.get('level'):
            if criteria['experienceLevel'].lower() not in job['level'].lower():
                continue
                
        if criteria.get('remoteOnly'):
            location = job.get('location', '').lower()
            if 'remote' not in location and 'work from home' not in location:
                continue
        
        # AI analysis
        ai_result = analyze_job_with_ai(job, criteria)
        job['ai_score'] = ai_result.get('score', 7)
        job['ai_analysis'] = ai_result.get('analysis', 'Job matches basic criteria')
        
        # Lower threshold to show more jobs
        if job['ai_score'] >= 6:
            filtered.append(job)
    
    print(f"After filtering: {len(filtered)} jobs")
    
    # Sort by AI score descending
    filtered.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
    
    return filtered

@app.route('/')
def index():
    return send_from_directory('..', 'Index.html') 

@app.route('/main')
def main_page():
    return send_from_directory('..', 'Main.html') 

@app.route('/contact')
def contact_page():
    return send_from_directory('..', 'Contact.html')  

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('..', filename) 

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.json
        print(f"Search request received: {data}")
        
        # Get geo_id for location
        location = data.get('location', '')
        if not location:
            return jsonify({"error": "Location is required"}), 400
            
        geo_id = get_geo_id(location)
        if not geo_id:
            return jsonify({"error": "Could not find location"}), 400
        
        print(f"Got geo_id: {geo_id} for location: {location}")
        
        # Step 1: Search for jobs (saves raw data to CSV)
        jobs = search_jobs(
            keywords=data.get('skills', ''),
            location=location,
            geo_id=geo_id,
            job_title=data.get('jobTitle', '')
        )
        
        print(f"Raw jobs found: {len(jobs)}")
        
        if not jobs:
            return jsonify({"jobs": [], "message": "No jobs found during scraping"})
        
        # Step 2: Run cleaner with user criteria
        print("\n🧹 Running intelligent cleaner...")
        
        cleaned_df = smart_clean_and_filter(data, 'linkedinjobs.csv')
        
        if cleaned_df is not None and len(cleaned_df) > 0:
            # Convert cleaned dataframe back to list of dictionaries
            jobs = cleaned_df.to_dict('records')
            print(f"Using {len(jobs)} intelligently filtered jobs")
        else:
            print("Cleaner returned no results, using raw scraped jobs")
            # Keep original jobs if cleaner fails
        
        # Filter jobs with AI
        filtered_jobs = filter_jobs(jobs, data)
        
        print(f"Filtered jobs: {len(filtered_jobs)}")
        
        if not filtered_jobs:
            # Return some jobs anyway if filtering removed everything
            for job in jobs[:10]:
                job['ai_score'] = 6
                job['ai_analysis'] = "Job shown due to no filtered results"
            filtered_jobs = jobs[:10]
        
        return jsonify({
            "jobs": filtered_jobs[:20],  # Return top 20 jobs
            "total_found": len(jobs),
            "ai_filtered": len(filtered_jobs)
        })
        
    except Exception as e:
        print(f"Error in search endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

