import requests
import urllib.parse

class MapsAgent:
    """
    ResearchMind Maps & Navigation Agent.
    Capabilities:
    - Search for locations (Geocoding)
    - Provide navigation links (Google Maps, OpenStreetMap)
    - Explain 'the right way' to go (General directions advice)
    """
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            "User-Agent": "ResearchMindAI/1.0 (contact: user@example.com)"
        }

    def find_location(self, query):
        """Find coordinates and details for a location."""
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        try:
            response = requests.get(self.nominatim_url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            if data:
                return {
                    "display_name": data[0]["display_name"],
                    "lat": data[0]["lat"],
                    "lon": data[0]["lon"]
                }
            return None
        except Exception as e:
            print(f"Error finding location: {e}")
            return None

    def get_navigation_link(self, destination, origin=None):
        """Generate a Google Maps navigation link."""
        dest_encoded = urllib.parse.quote(destination)
        if origin:
            origin_encoded = urllib.parse.quote(origin)
            return f"https://www.google.com/maps/dir/?api=1&origin={origin_encoded}&destination={dest_encoded}&travelmode=driving"
        else:
            return f"https://www.google.com/maps/search/?api=1&query={dest_encoded}"

    def guide_me(self, destination, current_location=None):
        """Provide 'brotherly' guidance to a destination."""
        loc_data = self.find_location(destination)
        if not loc_data:
            return {
                "message": f"I couldn't find '{destination}' on the map. Can you be more specific, like adding the city or street name?",
                "success": False
            }
        
        nav_link = self.get_navigation_link(destination, current_location)
        
        # Brotherly advice based on the location
        message = f"I've found {loc_data['display_name']} for you. "
        if current_location:
            message += f"Starting from {current_location}, I'll guide you through the best route. "
        else:
            message += "I'm ready to guide you there. "
        
        message += "Just click the map link below to see the right way. Stay safe on the road!"
        
        return {
            "message": message,
            "location": loc_data,
            "navigation_link": nav_link,
            "success": True
        }

if __name__ == "__main__":
    # Quick test
    agent = MapsAgent()
    print("Testing Maps Agent...")
    guide = agent.guide_me("Eiffel Tower, Paris")
    print(f"Message: {guide['message']}")
    print(f"Link: {guide['navigation_link']}")
