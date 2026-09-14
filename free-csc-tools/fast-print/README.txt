ONESTOP FAST DOCUMENT PRINT — P2P WEB DEPLOYMENT

Folder: /fast-print/

Pages:
- index.html  Portal
- admin.html  Admin print desk
- customer.html Customer send page
- print.html   Browser print editor
- webrtc.js    PeerJS/WebRTC transport
- styles.css   Shared styles

PRIVACY
- No Google Drive.
- No Google Sheets.
- No document database.
- Document bytes are transferred between customer and admin browsers using WebRTC.
- Received files exist only in browser memory and disappear when the page is closed/refreshed.

DEPLOYMENT
Use HTTPS hosting/GitHub Pages. Open /fast-print/admin.html on the shop computer. Click Start Receiver and share the temporary Connection ID with the customer. The customer opens /fast-print/customer.html, connects, selects images and sends the print request. The admin opens the received job in /fast-print/print.html.

IMPORTANT
The project uses PeerJS only for signaling/connection establishment. Internet access is required. The actual document transfer is peer-to-peer.
