import streamlit as st
import pandas as pd
from streamlit_folium import folium_static
import folium
from sklearn.cluster import KMeans
import requests
import time
import googlemaps

class HostelAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.gmaps = googlemaps.Client(key=self.api_key)
    
    def get_coordinates(self, place_name):
        geocode_result = self.gmaps.geocode(place_name)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            return None, None
    
    def fetch_places_nearby(self, location, radius, keyword, page_token=None):
        url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={location}&radius={radius}&keyword={keyword}&key={self.api_key}"
        if page_token:
            url += f"&pagetoken={page_token}"
        response = requests.get(url)
        data = response.json()
        time.sleep(2)  # Adding a delay of 2 seconds
        return data
    
    def fetch_category_count(self, lat, lng, category, radius):
        url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lng}&radius={radius}&keyword={category}&key={self.api_key}"
        response = requests.get(url)
        data = response.json()
        if 'results' in data:
            count = len(data['results'])
            print(f"Category: {category}, Count: {count}")
            return count
        elif data.get('status') == 'ZERO_RESULTS':
            print(f"No results found for category: {category}")
            return 0
        else:
            print(f"Error fetching results for category: {category}")
            return 0
        
    def clean_data(self, data):
        results = data.get('results', [])
        hostel_info = []

        for result in results:
            info = self.extract_info(result)
            if info:
                hostel_info.append(info)

        hostel_info_df = pd.DataFrame(hostel_info)
        return hostel_info_df
    
    def extract_info(self, result):
        if 'business_status' in result and 'geometry' in result and 'location' in result['geometry'] and 'lat' in result['geometry']['location'] and 'lng' in result['geometry']['location'] and 'name' in result:
            return {
                'business_status': result['business_status'],
                'latitude': result['geometry']['location']['lat'],
                'longitude': result['geometry']['location']['lng'],
                'name': result['name']
            }
        else:
            return None
    
    
    def calculate_amenity_counts(self, dataframe):
        RestList = []
        FruitList = []
        for lat, lng in zip(dataframe['latitude'], dataframe['longitude']):
            rest_count = self.fetch_category_count(lat, lng, "Restaurant|Cafe", 1000)
            fruit_count = self.fetch_category_count(lat, lng, "Fruit|Juice", 1000)
            RestList.append(rest_count)
            FruitList.append(fruit_count)
        dataframe['Restaurants'] = RestList
        dataframe['Fruits/juice,Vegetables'] = FruitList
        return dataframe
    
    def categorize_clusters(self, dataframe):
        cluster_means = dataframe.groupby('Cluster')[['Restaurants', 'Fruits/juice,Vegetables']].mean()
        dataframe['Amenity_Level'] = pd.cut(dataframe['Cluster'].astype(int).map(cluster_means['Restaurants']), bins=[-1, 5, 10, float('inf')], labels=['Low', 'Moderate', 'High'])
        return dataframe
    
    def perform_kmeans_clustering(self, dataframe):
        features = ['latitude', 'longitude', 'Restaurants', 'Fruits/juice,Vegetables']
        kmeans = KMeans(n_clusters=3, random_state=0)
        kmeans.fit(dataframe[features])
        dataframe['Cluster'] = kmeans.labels_.astype(str)
        return dataframe


class HostelApp:
    def __init__(self, api_key):
        self.analyzer = HostelAnalyzer(api_key)

class HostelApp:
    def __init__(self, api_key):
        self.analyzer = HostelAnalyzer(api_key)
    
    def run(self):
        st.title('Come Find Your Favorite Hostels at Hostelers!')

        place_input = st.text_input("Enter your starting location (Place Name or Latitude, Longitude)", "")
        radius = st.slider("Radius for hostels (in meters)", 1000, 10000, 5000, 1000)

        if place_input:
            # Fetch hostels nearby
            location = self.analyzer.get_coordinates(place_input)
            hostel_data = self.analyzer.fetch_places_nearby(f"{location[0]},{location[1]}", radius, "BoysHostel|GirlsHostel|Residency|Hostel|PG|House|Home")

            # Clean and preprocess the data
            hostel_info_df = self.analyzer.clean_data(hostel_data)

            # Calculate amenity counts
            hostel_info_df = self.analyzer.calculate_amenity_counts(hostel_info_df)

            # Perform K-means clustering
            clustered_hostel_data = self.analyzer.perform_kmeans_clustering(hostel_info_df)

            # Categorize clusters based on amenity levels
            clustered_hostel_data = self.analyzer.categorize_clusters(clustered_hostel_data)

            # Plot map with hostel locations and color-coded clusters
            map_clusters_hostel = folium.Map(location=[location[0], location[1]], zoom_start=12)

            # Add marker for user's entered location
            if place_input:
                marker_popup = place_input if ',' in place_input else place_input
                folium.Marker([location[0], location[1]], popup=marker_popup, icon=folium.Icon(color='red')).add_to(map_clusters_hostel)

            # Add hostel markers with cluster coloring
            for lat, lon, cluster, name, amenity_level in zip(clustered_hostel_data['latitude'], clustered_hostel_data['longitude'], clustered_hostel_data['Cluster'], clustered_hostel_data.get('name', ''), clustered_hostel_data['Amenity_Level']):
                popup_text = f"Name: {name}, Amenity Level: {amenity_level}" if name else "Name: Not Available"
                color = 'green' if amenity_level == 'High' else 'yellow' if amenity_level == 'Moderate' else 'red'
                folium.CircleMarker([lat, lon], radius=5, color=color, fill=True, fill_color=color, fill_opacity=0.7, popup=popup_text).add_to(map_clusters_hostel)
            
            # Display the map
            folium_static(map_clusters_hostel)



def main():
    api_key = "AIzaSyBHxU_STqvjom_F7uK80-g8-wBljzP4UYg"
    app = HostelApp(api_key)
    app.run()

if __name__ == '__main__':
    main()
