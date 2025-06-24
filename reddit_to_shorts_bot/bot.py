# Main script for Reddit to Shorts Bot
import os
from dotenv import load_dotenv
import praw
import time # For potential rate limiting in the future
from gtts import gTTS
from bs4 import BeautifulSoup
import re

# Ensure output directory exists
OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def clean_text(text):
    """Cleans text from HTML and basic markdown for TTS."""
    # Remove HTML using BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()

    # Remove URLs (they are not good for TTS)
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

    # Remove common markdown formatting characters like *, _, `
    # This is a simple approach; more complex markdown parsing might be needed for some cases
    text = re.sub(r'[*_`]', '', text)

    # Handle markdown links: [link text](url) -> link text
    # Corrected regex for markdown links:
    text = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', text)

    # Normalize whitespace (multiple spaces/newlines to one)
    text = re.sub(r'\s+', ' ', text).strip()
    # Consolidate multiple newlines to single, then strip leading/trailing newlines
    text = re.sub(r'\n\s*\n+', '\n', text).strip()

    # Further specific cleaning (example: removing "edit:", "tl;dr")
    # Make these case-insensitive and ensure they remove the rest of the line if they are at the start
    text = re.sub(r'^(edit|update):.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'^(tl;dr|tldr):.*$', '', text, flags=re.IGNORECASE | re.MULTILINE)

    # Remove any remaining leading/trailing whitespace from the whole text
    text = text.strip()

    return text

def generate_tts(text, output_filepath):
    """Generates TTS audio from text and saves it to a file."""
    try:
        print(f"Generating TTS for: {output_filepath}...")
        if not text.strip():
            print(f"Skipping TTS generation for {output_filepath} due to empty text.")
            return False
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_filepath)
        print(f"Successfully saved audio to {output_filepath}")
        return True
    except Exception as e:
        print(f"Error during TTS generation for {output_filepath}: {e}")
        return False

def fetch_reddit_stories():
    """
    Fetches stories from specified subreddits using PRAW.
    Filters posts based on length, NSFW status, and type.
    """
    try:
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_user_agent = os.getenv("REDDIT_USER_AGENT")

        subreddits_str = os.getenv("SUBREDDITS", "AskReddit")
        post_limit = int(os.getenv("POST_LIMIT", 5))
        min_story_length = int(os.getenv("MIN_STORY_LENGTH", 500)) # Min char length for post.selftext

        if not all([reddit_client_id, reddit_client_secret, reddit_user_agent]):
            print("Error: Reddit API credentials not found in .env file. Please create .env from .env.example and fill it.")
            return []

        # Check if credentials are placeholders
        if "YOUR_REDDIT_CLIENT_ID" in reddit_client_id or \
           "YOUR_REDDIT_CLIENT_SECRET" in reddit_client_secret or \
           "YOUR_REDDIT_USER_AGENT" in reddit_user_agent:
            print("Error: Placeholder Reddit API credentials found.")
            print("Please replace placeholder values in your .env file with actual credentials.")
            return []

        reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent,
            read_only=True
        )
        print(f"PRAW instance created for user agent: {reddit_user_agent}")

    except Exception as e:
        print(f"Error during PRAW initialization or config loading: {e}")
        return []

    target_subreddits = [s.strip() for s in subreddits_str.split(',')]
    fetched_stories_data = []

    print(f"Fetching up to {post_limit} stories from each of these subreddits: {target_subreddits}")
    print(f"Minimum story length (cleaned selftext): {min_story_length} characters.")

    for subreddit_name in target_subreddits:
        try:
            print(f"\nProcessing subreddit: r/{subreddit_name}")
            subreddit = reddit.subreddit(subreddit_name)
            hot_posts = subreddit.hot(limit=post_limit * 3) # Fetch more to filter

            stories_from_this_sub = 0
            for post in hot_posts:
                if stories_from_this_sub >= post_limit:
                    break

                if not post.is_self or not getattr(post, 'selftext', None) or post.stickied or post.over_18:
                    continue

                # Clean title and selftext separately
                # Title cleaning is mostly for filename and optional TTS prefix
                temp_cleaned_title = clean_text(post.title)
                cleaned_selftext = clean_text(post.selftext)

                if len(cleaned_selftext) >= min_story_length:
                    story_data = {
                        'id': post.id,
                        'title': post.title,
                        'cleaned_title': temp_cleaned_title, # Use this for TTS if needed
                        'selftext': post.selftext,
                        'cleaned_selftext': cleaned_selftext, # Main content for TTS & length check
                        'permalink': f"https://reddit.com{post.permalink}",
                        'score': post.score,
                        'subreddit': subreddit_name
                    }
                    fetched_stories_data.append(story_data)
                    stories_from_this_sub += 1
                    print(f"  + Suitable story: {post.id} - {post.title[:50]}... (Cleaned length: {len(cleaned_selftext)})")

            if stories_from_this_sub == 0:
                print(f"  - No suitable stories found in r/{subreddit_name} matching all criteria after cleaning.")

        except praw.exceptions.PRAWException as e:
            print(f"  ! PRAW Error processing subreddit r/{subreddit_name}: {e}")
            continue
        except Exception as e:
            print(f"  ! An unexpected error occurred with r/{subreddit_name}: {e}")
            continue

    print(f"\nTotal suitable stories collected: {len(fetched_stories_data)}")
    return fetched_stories_data

def main():
    load_dotenv()
    print("--- Reddit Story to Audio Bot Initialized ---")

    # This script will still fail to fetch actual stories if Reddit credentials are placeholders
    # The following print statement is for testing the credential loading part
    if "YOUR_REDDIT_CLIENT_ID" in os.getenv("REDDIT_CLIENT_ID", ""):
         print("WARNING: Using placeholder Reddit credentials. Story fetching will likely fail or return limited data.")

    stories = fetch_reddit_stories()

    if stories:
        print(f"\n--- Processing {len(stories)} Fetched Stories for TTS ---")
        for i, story in enumerate(stories):
            print(f"\nProcessing story {i+1}/{len(stories)}: ID: {story['id']}, Subreddit: r/{story['subreddit']}")
            print(f"Original Title: {story['title']}")

            # Sanitize title for filename
            # Replace non-alphanumeric characters (except spaces) with underscore, then replace spaces with underscore
            safe_title_part = re.sub(r'[^\w\s-]', '_', story['cleaned_title'])
            safe_title_part = re.sub(r'\s+', '_', safe_title_part).strip('_')
            safe_filename_base = f"{story['subreddit']}_{safe_title_part[:50]}_{story['id']}"

            audio_filepath = os.path.join(OUTPUT_DIR, f"{safe_filename_base}.mp3")
            text_filepath = os.path.join(OUTPUT_DIR, f"{safe_filename_base}.txt")

            # Save cleaned text with metadata
            try:
                with open(text_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {story['title']}\n")
                    f.write(f"Cleaned Title: {story['cleaned_title']}\n")
                    f.write(f"Subreddit: r/{story['subreddit']}\n")
                    f.write(f"Reddit Link: {story['permalink']}\n")
                    f.write(f"Score: {story['score']}\n\n")
                    f.write("--- Cleaned Selftext ---\n")
                    f.write(story['cleaned_selftext'])
                print(f"  Successfully saved cleaned text to {text_filepath}")
            except Exception as e:
                print(f"  Error saving text file {text_filepath}: {e}")

            # Generate TTS from cleaned title + cleaned selftext
            text_for_tts = f"{story['cleaned_title']}. {story['cleaned_selftext']}"
            if not generate_tts(text_for_tts, audio_filepath):
                 print(f"  TTS generation failed for story ID {story['id']}.")

            time.sleep(0.5) # Brief pause between TTS generations

    else:
        print("No stories were fetched that match the criteria, so no TTS generation.")

    print("\n--- Bot script finished ---")

if __name__ == "__main__":
    main()
