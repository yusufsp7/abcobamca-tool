import streamlit as st
import requests
from datetime import datetime, timedelta

# YouTube API Key
# IMPORTANT: Replace "Enter your API Key here" with your actual YouTube Data API v3 key.
# You can obtain this from the Google Cloud Console.
# For deployment on Streamlit Cloud, it is highly recommended to use st.secrets.
# Create a file named .streamlit/secrets.toml in your GitHub repository with the content:
# API_KEY="YOUR_ACTUAL_API_KEY_HERE"
API_KEY = st.secrets["AIzaSyDnAbJ6G1mHfgjaa7gM_eNWvjQw95T-j8w"] 
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

# Streamlit App Title and Description
st.set_page_config(page_title="YouTube Viral Topics Tool", layout="centered")
st.title("YouTube Viral Topics Tool")
st.markdown(
    """
    This tool helps you discover potentially viral YouTube topics by searching for videos
    related to specific keywords from channels with fewer than 3,000 subscribers.
    """
)

# Input Fields
st.header("Search Parameters")
days = st.number_input(
    "Enter Days to Search (1-30):", 
    min_value=1, 
    max_value=30, 
    value=5,
    help="Number of days back from today to search for videos."
)

# List of broader keywords
keywords = [
    "Affair Relationship Stories", "Reddit Update", "Reddit Relationship Advice", 
    "Reddit Relationship", "Reddit Cheating", "AITA Update", "Open Marriage", 
    "Open Relationship", "X BF Caught", "Stories Cheat", "X GF Reddit", 
    "AskReddit Surviving Infidelity", "GurlCan Reddit", 
    "Cheating Story Actually Happened", "Cheating Story Real", 
    "True Cheating Story", "Reddit Cheating Story", "R/Surviving Infidelity", 
    "Surviving Infidelity", "Reddit Marriage", "Wife Cheated I Can't Forgive", 
    "Reddit AP", "Exposed Wife", "Cheat Exposed"
]

# Display keywords for user reference
with st.expander("View Search Keywords"):
    st.write("The tool will search for videos using the following keywords:")
    st.code("\n".join(keywords), language="text")

# Fetch Data Button
if st.button("Fetch Data", help="Click to start searching for videos."):
    # The API_KEY check is now implicitly handled by st.secrets, which will raise an error
    # if the key is not found, preventing the app from running without it.
    try:
        # Calculate date range for the API query
        start_date = (datetime.utcnow() - timedelta(days=int(days))).isoformat("T") + "Z"
        all_results = []
        
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Iterate over the list of keywords
        for i, keyword in enumerate(keywords):
            status_text.text(f"Searching for keyword: {keyword} ({i+1}/{len(keywords)})")
            progress_bar.progress((i + 1) / len(keywords))

            # Define search parameters for YouTube API
            search_params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "viewCount", # Order by view count to find popular videos
                "publishedAfter": start_date, # Filter by publication date
                "maxResults": 5, # Fetch up to 5 videos per keyword
                "key": API_KEY,
            }

            # Fetch video data from YouTube Search API
            response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            data = response.json()

            # Check if "items" key exists and contains data
            if "items" not in data or not data["items"]:
                st.warning(f"No videos found for keyword: '{keyword}' in the specified date range.")
                continue

            videos = data["items"]
            # Extract video IDs and channel IDs from the search results
            video_ids = [video["id"]["videoId"] for video in videos if "id" in video and "videoId" in video["id"]]
            channel_ids = [video["snippet"]["channelId"] for video in videos if "snippet" in video and "channelId" in video["snippet"]]

            if not video_ids:
                st.warning(f"Skipping keyword: '{keyword}' due to missing video IDs.")
                continue
            if not channel_ids:
                st.warning(f"Skipping keyword: '{keyword}' due to missing channel IDs.")
                continue

            # Fetch video statistics (views, likes, etc.)
            stats_params = {
                "part": "statistics", 
                "id": ",".join(video_ids), 
                "key": API_KEY
            }
            stats_response = requests.get(YOUTUBE_VIDEO_URL, params=stats_params)
            stats_response.raise_for_status()
            stats_data = stats_response.json()

            if "items" not in stats_data or not stats_data["items"]:
                st.warning(f"Failed to fetch video statistics for keyword: '{keyword}'.")
                continue

            # Fetch channel statistics (subscriber count)
            channel_params = {
                "part": "statistics", 
                "id": ",".join(channel_ids), 
                "key": API_KEY
            }
            channel_response = requests.get(YOUTUBE_CHANNEL_URL, params=channel_params)
            channel_response.raise_for_status()
            channel_data = channel_response.json()

            if "items" not in channel_data or not channel_data["items"]:
                st.warning(f"Failed to fetch channel statistics for keyword: '{keyword}'.")
                continue

            stats_map = {item["id"]: item["statistics"] for item in stats_data["items"]}
            channels_map = {item["id"]: item["statistics"] for item in channel_data["items"]}

            # Collect results, filtering by subscriber count
            for video in videos:
                video_id = video["id"]["videoId"]
                channel_id = video["snippet"]["channelId"]
                
                video_stats = stats_map.get(video_id, {})
                channel_stats = channels_map.get(channel_id, {})

                title = video["snippet"].get("title", "N/A")
                description = video["snippet"].get("description", "")
                # Truncate description for display
                truncated_description = (description[:200] + '...') if len(description) > 200 else description
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Get view count, default to 0 if not found
                views = int(video_stats.get("viewCount", 0))
                # Get subscriber count, default to 0 if not found
                subs = int(channel_stats.get("subscriberCount", 0))

                # Only include channels with fewer than 3,000 subscribers
                if subs < 3000: 
                    all_results.append({
                        "Title": title,
                        "Description": truncated_description,
                        "URL": video_url,
                        "Views": views,
                        "Subscribers": subs,
                        "Keyword": keyword # Add keyword for context
                    })
        
        progress_bar.empty()
        status_text.empty()

        # Display results
        if all_results:
            st.success(f"Found {len(all_results)} results across all keywords for channels with < 3,000 subscribers!")
            # Sort results by views in descending order
            all_results_sorted = sorted(all_results, key=lambda x: x["Views"], reverse=True)
            
            for result in all_results_sorted:
                st.markdown(
                    f"**Keyword:** `{result['Keyword']}`  \n"
                    f"**Title:** {result['Title']}  \n"
                    f"**Description:** {result['Description']}  \n"
                    f"**URL:** [Watch Video]({result['URL']})  \n"
                    f"**Views:** {result['Views']:,}  \n" # Format views with commas
                    f"**Subscribers:** {result['Subscribers']:,}" # Format subscribers with commas
                )
                st.write("---")
        else:
            st.warning("No results found for channels with fewer than 3,000 subscribers based on your criteria.")

    except requests.exceptions.RequestException as req_err:
        st.error(f"Network or API request error: {req_err}. Please check your internet connection and API key.")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

st.markdown("---")
st.info("Developed with Streamlit and YouTube Data API v3.")
