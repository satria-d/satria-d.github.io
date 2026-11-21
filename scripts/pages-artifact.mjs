// GitHub's upload response can precede artifact visibility to deployment APIs.
export async function waitForArtifact(listArtifacts, {
  expectedId, attempts = 6,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
  onRetry = () => {},
} = {}) {
  if (!expectedId) throw new Error('Pages upload did not return an artifact ID.');
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      const artifacts = await listArtifacts();
      const artifact = artifacts.find(a => String(a.id) === String(expectedId)
        && a.name === 'github-pages' && !a.expired);
      if (artifact) return artifact;
    } catch (error) {
      // Authentication/configuration errors need a real fix, not repeated requests.
      if (error.status !== 429 && !(error.status >= 500)) throw error;
    }
    if (attempt < attempts) {
      const delay = Math.min(5000 * 2 ** (attempt - 1), 20000);
      onRetry(attempt, delay);
      await sleep(delay);
    }
  }
  throw new Error('Uploaded Pages artifact is not visible yet; encrypted snapshot remains saved.');
}
