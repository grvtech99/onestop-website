/**
 * ONESTOP Background Remover Proxy
 * Deploy as a Google Apps Script Web App:
 * Execute as: Me
 * Who has access: Anyone
 *
 * Frontend sends JSON:
 * {
 *   fileName: "photo.jpg",
 *   mimeType: "image/jpeg",
 *   base64: "...."
 * }
 *
 * Apps Script sends the image server-side to BGNinja,
 * then returns the finished PNG as base64.
 */

const BGNINJA_URL = 'https://bgninja.com/api/remove';

function doGet() {
  return json_({ ok: true, service: 'ONESTOP Background Remover Proxy' });
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return json_({ ok: false, error: 'Empty request.' });
    }

    const input = JSON.parse(e.postData.contents || '{}');
    if (!input.base64) return json_({ ok: false, error: 'Missing image data.' });

    const mimeType = String(input.mimeType || 'image/jpeg');
    const fileName = String(input.fileName || 'image.jpg');

    if (!/^image\/(jpeg|png|webp|heic|heif)$/i.test(mimeType)) {
      return json_({ ok: false, error: 'Unsupported image type.' });
    }

    const raw = Utilities.base64Decode(String(input.base64));
    const imageBlob = Utilities.newBlob(raw, mimeType, fileName);

    const response = UrlFetchApp.fetch(BGNINJA_URL, {
      method: 'post',
      payload: {
        file: imageBlob,
        src: 'onestop-background-remover'
      },
      muteHttpExceptions: true,
      followRedirects: true
    });

    const status = response.getResponseCode();
    const headers = response.getHeaders();
    const contentType = String(headers['Content-Type'] || headers['content-type'] || '');

    if (status !== 200) {
      let message = 'Background removal service failed.';
      try {
        const data = JSON.parse(response.getContentText());
        message = data.error || data.detail || message;
      } catch (_) {}
      return json_({ ok: false, status, error: message });
    }

    const png = response.getBlob();
    const pngType = String(png.getContentType() || contentType || '');
    if (!pngType.toLowerCase().includes('image/png')) {
      return json_({ ok: false, status: 502, error: 'Unexpected response from background-removal service.' });
    }

    return json_({
      ok: true,
      mimeType: 'image/png',
      base64: Utilities.base64Encode(png.getBytes())
    });

  } catch (err) {
    console.error(err);
    return json_({ ok: false, status: 500, error: String(err && err.message || err) });
  }
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
