# YouTube upload quota increase (for the owner to submit)

All 4 YouTube channels (Snortlo, Keegix, Staffkin, Waypoint Software) post through one Google Cloud project
(the one Postiz uses). The free daily quota is 10,000 units and each upload costs about 1,600, so about 6 uploads
a day are shared by all channels. Asking for more is free.

Form: https://support.google.com/youtube/contact/yt_api_form ("YouTube API Services - Audit and Quota Extension").
You'll need the Google Cloud project number (Google Cloud console, project picker, Project info card).

Suggested answers:
- **What does your API client do?** It's a self-hosted social media scheduler (Postiz, open source) that a small
  Nova Scotia business uses to upload and schedule its own original videos to the owner's own YouTube channels.
  No other users, no viewer data collected, no reads of other people's content.
- **Which API features?** videos.insert (uploads), thumbnails.set, and reading our own channels' basic info.
- **Why more quota?** We publish original videos to 4 channels we own: a daily Shorts channel plus two weekly
  podcasts with Shorts. That needs about 8 to 10 uploads a day; the default allows about 6.
- **Requested quota:** 20,000 units per day.
- **Users:** one (the channel owner). Data is not shared, sold or stored beyond what Postiz needs to post.

Google may ask for a short screen recording of the upload flow in Postiz and links to the channels.
Once approved: put Snortlo's cap back to 5 in NIGHTLY.md and the "Snortlo nightly story" task.
