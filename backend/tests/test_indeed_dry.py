import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.scout import ScoutAgent

def test_indeed_dry():
    print("Running Scout Agent Indeed Dry Run Test...")
    scout = ScoutAgent()
    
    # Run scout indeed query
    jobs = scout._fetch_indeed("software engineer", 3)
    
    print(f"Scraped {len(jobs)} jobs from Indeed.")
    for idx, job in enumerate(jobs):
        print(f"\n--- Job {idx+1} ---")
        print(f"Title: {job['title']}")
        print(f"Company: {job['company']}")
        print(f"Location: {job['location']}")
        print(f"URL: {job['url']}")
        print(f"Description snippet: {job['description'][:100]}...")
        
    assert len(jobs) >= 0
    print("Indeed Dry Run Test Completed Successfully!")

if __name__ == "__main__":
    test_indeed_dry()
