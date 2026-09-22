# Gaurav's World — Manual Cover Image Upload

This automation creates review-only bilingual draft JSON files. It does not publish to the live blog.

## Image mode

Paid AI image generation has been removed from `scripts/run.py`. Each draft is saved with:

- `image_status: manual_pending`
- `image_upload_filename: <draft-slug>.png`
- `cover_image: null`

## Upload a cover image

1. Run the GitHub Actions workflow and wait for text-draft generation to finish.
2. Open the `gauravs-world-automation` branch in the repository.
3. Open `automation/gauravs-world/images/` (create the folder if it is not shown).
4. Upload a PNG cover image using the exact `image_upload_filename` from that draft's JSON.
5. Commit the image to `gauravs-world-automation`.
6. Re-run the workflow if you want the draft JSON to recognize the image as `manual_uploaded`.

## Important limitations

- This upload is stored in the repository; it does not automatically appear in the live blog or a web-based editorial dashboard.
- The current workflow's text-generation step still calls the OpenAI API and requires API quota. Manual image upload removes image-generation API usage only; it does not replace text generation.
- Drafts are based on RSS metadata and require source checking and editorial fact-checking.
- Do not commit API keys or other secrets.
