import sys
import subprocess
from geopy.geocoders import Nominatim

def get_geo_id(place_name):
    geolocator = Nominatim(user_agent="job_finder_app")
    location = geolocator.geocode(place_name)
    if location:
        return location.raw.get('place_id')
    else:
        return None

def main():
    # Get location from command line or input
    if len(sys.argv) > 1:
        place_name = ' '.join(sys.argv[1:])
    else:
        place_name = input("Enter location: ").strip()

    geo_id = get_geo_id(place_name)

    if geo_id:
        print(f"Found GEO ID: {geo_id}")

        # Call scraper.py, passing geo_id as command line argument
        # Adjust the way scraper.py accepts input based on your implementation
        try:
            subprocess.run(['python', 'scraper.py', '--geo_id', str(geo_id)], check=True)
        except subprocess.CalledProcessError as e:
            print("Error running scraper.py:", e)
    else:
        print("Could not find GEO ID for the location.")

if __name__ == "__main__":
    main()
