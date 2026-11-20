# Radar Karier · GitHub Pages

Public web shell, encrypted career data. Python public-source collectors run every six hours on GitHub Actions. No GPT, OpenAI service, or AI API is used.

## First setup

Enable repository Settings → Pages → Source: GitHub Actions. Add repository Actions secret **RADAR_PASSWORD** with a unique password of at least 16 characters (a long random passphrase is best). Run Actions → Radar Karier → Run workflow. Use the same password on the published site. Never commit it.

## Privacy

Only `web/` is published. Data is encrypted before commit and upload with AES-256-GCM; PBKDF2-SHA256 uses 600,000 iterations, a fresh 32-byte salt and 12-byte nonce each time. Decryption happens in the browser. No password, decryption key, or decrypted data is saved in browser storage. The raw snapshot exists only in a temporary runner directory, is removed after collection and is not logged or uploaded as an artifact.

The shell and encrypted bytes are public. This is encryption, not server-side authentication: weak passwords can be guessed offline, and anyone who knows the password can read and share the data. Use a unique strong password. Historical ciphertext remains in Git history; changing the password does not revoke old copies. Password changes deliberately fail closed if old data cannot be decrypted; perform a deliberate re-encryption migration before rotating.

Old private project `satria-d/radar-karier` remains private and retains its existing data. This public Pages repo does not expose that repo or its plaintext records. The standalone collector initially discovers public jobs itself.

## Source integrity

Uses public LinkedIn, JobStreet, Glints, Kalibrr, Dealls and company career pages plus GoTo and Amar Bank Lever feeds. Access failures are recorded and do not close jobs. Posting dates only come from source dates; unknown dates stay empty. Existing data survives source outages. The filter is a career heuristic, not a guarantee of suitability. Source blocks and changing markup can reduce coverage.

## Checks

`node --test tests/*.test.mjs` verifies correct password, incorrect password, authenticated tamper detection and randomized encryption. `node --check web/app.mjs` validates JavaScript syntax.
