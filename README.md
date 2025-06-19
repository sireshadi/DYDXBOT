# Unhyreable - Transparent Bitcoin Mining Landing Page

This repository contains the HTML code for the Unhyreable.com landing page, focused on transparent Bitcoin mining services.

## Overview

The landing page is a single HTML file (`index.html`) designed to:
- Clearly present the value proposition of Unhyreable.
- Explain the investment process in simple steps.
- Build trust by providing information about the operation.
- Detail the investment tiers/packages offered.
- Answer frequently asked questions (FAQs).
- Capture leads through a contact form.
- Provide a downloadable prospectus.

The page is built using:
- HTML5
- Tailwind CSS for styling
- Google Fonts (Inter)
- Lucide Icons
- Custom inline CSS and JavaScript for specific functionalities like the FAQ accordion and prospectus download.

## How to View

1.  Clone or download this repository to your local machine.
2.  Navigate to the repository's root directory.
3.  Open the `index.html` file in any modern web browser (e.g., Chrome, Firefox, Safari, Edge).

## Key Features Implemented

- **Responsive Design:** Adapts to different screen sizes using Tailwind CSS.
- **Interactive FAQ:** Accordion-style FAQ section.
- **Prospectus Download:** Button to download a text-based prospectus.
- **Lead Generation Form:** HTML form structure (requires backend setup, e.g., Formspree, for full functionality).
- **Semantic HTML:** Structured with semantic tags like `<main>`, `<section>`, `<footer>`.
- **Performance Considerations:** Scripts are deferred to prevent render-blocking.

## Placeholders & TODOs

Please note the following placeholders in `index.html` that need to be updated with actual information:

- **Founder's Name:** "John Doe" in the "Our Operation" section.
- **Mining Hardware Image:** The placeholder image `https://placehold.co/600x400/...` should be replaced with a real photo of the mining hardware.
- **Hashrate Estimates:** "Estimated X TH/s" and "Estimated Y TH/s" in the "Investment Tiers" section.
- **Form Endpoint:** `YOUR_FORM_ENDPOINT` in the `form` tag's `action` attribute needs to be replaced with a valid Formspree (or other service) URL.

## Deploying to Netlify (Caveats)

This project can be configured for deployment to Netlify using the provided `netlify.toml` and `netlify_functions/api_handler.py`. However, due to the nature of serverless environments and the current architecture of this Flask application, there are significant caveats for a production deployment:

1.  **Database (SQLite):**
    *   **Issue:** The application uses SQLite, which stores the database in a local file (`instance/unhyreable.db`). Netlify serverless functions have ephemeral filesystems. This means any data written to the SQLite database (new users, pages, links, etc.) will likely be lost between function invocations or will not be persisted reliably.
    *   **Recommendation:** For a functional deployment on Netlify, you **must migrate to a cloud-hosted database** (e.g., Neon, Supabase, PlanetScale, AWS RDS, Google Cloud SQL, FaunaDB). The `SQLALCHEMY_DATABASE_URI` in `backend/app.py` should be configured via Netlify environment variables to point to your cloud database.

2.  **User File Uploads (Local Storage):**
    *   **Issue:** User-uploaded assets (images, favicons) are currently stored in the `instance/user_uploads/` directory on the server's local filesystem. Similar to SQLite, this storage is ephemeral in Netlify serverless functions. Uploaded files will not persist.
    *   **Recommendation:** For persistent file storage on Netlify, integrate **a dedicated cloud object storage service** (e.g., AWS S3, Google Cloud Storage, Cloudinary). The file upload logic in `backend/app.py` needs to be modified to upload files to this service, and asset URLs will need to reference the object storage.

3.  **`app.instance_path` Reliance:**
    *   **Issue:** The application relies on `app.instance_path` for both the SQLite database and local file uploads. This path is not reliably persistent or writable in a scalable way in serverless environments.
    *   **Recommendation:** Transitioning to cloud databases and object storage (as mentioned above) will reduce the reliance on a persistent local `instance_path`.

4.  **Session Management:**
    *   Flask's default client-side cookie-based sessions should work. Ensure your `app.secret_key` is set as a secure environment variable in your Netlify deployment settings.

**Conclusion for Netlify Deployment:**
While `netlify.toml` and the serverless handler enable the Flask app to *run* on Netlify, **the current data persistence strategy (SQLite and local file uploads) is not compatible with a production serverless environment.** You will need to re-architect data and file storage to use cloud-based services for a stable and scalable deployment on Netlify.
