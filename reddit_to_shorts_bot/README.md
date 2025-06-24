# Reddit to Audio Bot for YouTube Shorts

This Python script fetches stories from specified subreddits, cleans the text content, and generates audio narration files (MP3) using Google Text-to-Speech. The generated audio and cleaned text can then be used as a basis for creating YouTube Shorts or other video content.

## Features

- Fetches top/hot posts from configurable subreddits.
- Filters posts by length, NSFW status, and type (text posts only).
- Cleans HTML and basic markdown from story text.
- Generates MP3 audio narration for each suitable story using gTTS.
- Saves cleaned text and audio files to an `output/` directory.
- Configuration via a `.env` file for API keys and bot parameters.

## Setup Instructions

### 1. Prerequisites
- Python 3.7+
- Pip (Python package installer)

### 2. Clone/Download Files
- If you have Git, clone the repository.
- Otherwise, download the contents of the `reddit_to_shorts_bot` directory.

### 3. Create a Virtual Environment (Recommended)
It's good practice to use a virtual environment to manage project dependencies.
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies
Install the required Python libraries using `pip`:
```bash
pip install -r requirements.txt
```

### 5. Set Up Reddit API Credentials

You need to register a script app with Reddit to get API credentials.

1.  **Go to Reddit Apps:** Navigate to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) while logged into your Reddit account.
2.  **Create a new app:**
    *   Click "are you a developer? create an app..."
    *   **Name:** Give your app a name (e.g., "MyShortsBot").
    *   **Type:** Select **"script"**.
    *   **Description:** (Optional) e.g., "Bot to fetch stories for YouTube Shorts."
    *   **About URL:** (Optional)
    *   **Redirect URI:** For a script app, you can often use `http://localhost:8080` (it won't actually be used for this bot's authentication flow).
    *   Click "create app".
3.  **Get Credentials:**
    *   Once created, you'll see your app listed.
    *   The **Client ID** is the string of characters under your app's name (e.g., `P1a2B3c4D5e6F7`).
    *   The **Client Secret** is the string labeled "secret" (e.g., `XyZ123abcDEF456GHIjkl789mno`).
4.  **Create User Agent:** This is a string that identifies your script. A good format is `<platform>:<app_id>:<version_string> (by /u/<your_reddit_username>)`. For example: `Python:RedditToShortsBot:v0.1 (by /u/YourUsername)`.

### 6. Configure the Bot
1.  In the `reddit_to_shorts_bot` directory, find the `.env.example` file.
2.  **Create a copy** of this file and name it `.env`.
3.  Open the `.env` file and replace the placeholder values with your actual Reddit API credentials and desired settings:
    ```ini
    REDDIT_CLIENT_ID='YOUR_REDDIT_CLIENT_ID'
    REDDIT_CLIENT_SECRET='YOUR_REDDIT_CLIENT_SECRET'
    REDDIT_USER_AGENT='YOUR_REDDIT_USER_AGENT'

    SUBREDDITS='AskReddit,TIFU,nosleep' # Comma-separated, no spaces around commas
    POST_LIMIT=5 # Number of posts to fetch per subreddit
    MIN_STORY_LENGTH=500 # Minimum character length for cleaned story text
    ```
    **Important:** Do NOT commit your `.env` file to version control if this is a public repository. The `.gitignore` file is already set up to ignore it.

## Running the Script

Once set up, you can run the bot from within the `reddit_to_shorts_bot` directory (and with your virtual environment activated, if you used one):

```bash
python bot.py
```

The script will print progress messages to the console.

## Expected Output

-   **Audio Files:** MP3 audio narrations will be saved in the `reddit_to_shorts_bot/output/` directory. Filenames will typically be in the format `subreddit_sanitizedtitle_postid.mp3`.
-   **Text Files:** Cleaned text versions of the stories, along with metadata (title, link, score), will be saved in the `reddit_to_shorts_bot/output/` directory with corresponding `.txt` extensions.

## Next Steps for You (Video Creation)

This script **only generates the audio narration and cleaned text**. To create YouTube Shorts, you will need to:

1.  **Source Visuals:** Find or create relevant background video clips, images, or gameplay footage.
2.  **Video Editing:** Use video editing software (e.g., DaVinci Resolve, Adobe Premiere Pro, CapCut, or programmatic tools like MoviePy if you want to automate further) to:
    *   Combine the generated MP3 audio with your visuals.
    *   Add text overlays or subtitles (highly recommended for Shorts).
    *   Ensure the video is in a vertical aspect ratio (e.g., 1080x1920) and under 60 seconds.
3.  **Upload to YouTube:** Upload your finished videos to YouTube Shorts.

## Automation (e.g., 5 Videos a Day)

To automate running this script (e.g., to fetch content for 5 videos daily):

-   **Scheduling:** You'll need to set up a scheduler on your computer or server.
    *   **Linux/macOS:** Use `cron`.
    *   **Windows:** Use Task Scheduler.
-   **Script Modification (Optional):** You might want to modify the script to fetch a specific number of stories per run if you schedule it multiple times a day, or ensure it doesn't re-process already completed stories (e.g., by keeping a log of processed post IDs). The current script fetches `POST_LIMIT` from each subreddit per run.

## Basic Troubleshooting

-   **Credentials Error:** If you see "Reddit API credentials not found" or "Placeholder Reddit API credentials found," double-check your `.env` file is correctly named, in the right directory, and has the correct, non-placeholder values.
-   **PRAW Errors:** Ensure your API credentials are correct and your app type is "script". Reddit might have rate limits, though PRAW attempts to handle these.
-   **gTTS Errors:** `gTTS` usually works offline but might occasionally have issues. Ensure you have a stable internet connection when it first runs if it needs to download language data (though this is rare).
-   **No Stories Found:** Try different subreddits, adjust `POST_LIMIT`, or lower `MIN_STORY_LENGTH` (though very short stories might not make good videos). Some subreddits have stricter posting rules or fewer text posts.

---

Remember to use this bot responsibly and respect Reddit's terms of service and the content creators.
