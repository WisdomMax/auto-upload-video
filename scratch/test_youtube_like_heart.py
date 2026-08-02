import youtube_comments

youtube = youtube_comments.get_youtube_service()
if not youtube:
    print("No service")
    exit(1)

# Test available methods on youtube.comments()
methods = [m for m in dir(youtube.comments()) if not m.startswith("_")]
print("Available comments API methods:", methods)

