import {test} from 'node:test';
import assert from 'node:assert/strict';
import {waitForArtifact} from '../scripts/pages-artifact.mjs';
const artifact = {id: 42, name: 'github-pages', expired: false};
test('Waits for the exact uploaded artifact after temporarily empty metadata', async () => {
  let calls = 0; const delays = [];
  const result = await waitForArtifact(async () => ++calls < 3
    ? [{...artifact, id: 41}] : [artifact],
    {expectedId: '42', sleep: async ms => delays.push(ms)});
  assert.equal(result, artifact);
  assert.equal(calls, 3);
  assert.deepEqual(delays, [5000, 10000]);
});
test('Expired or missing artifacts fail within a bounded number of checks', async () => {
  let calls = 0; let sleeps = 0;
  await assert.rejects(waitForArtifact(async () => {
    calls++; return [{...artifact, expired: true}];
  }, {expectedId: 42, attempts: 3, sleep: async () => sleeps++}), /not visible/);
  assert.equal(calls, 3); assert.equal(sleeps, 2);
  await assert.rejects(waitForArtifact(async () => [artifact]), /artifact ID/);
});
test('Retries transient API failures but fails immediately on denied access', async () => {
  let calls = 0;
  assert.equal(await waitForArtifact(async () => {
    if (++calls === 1) throw Object.assign(new Error('Unavailable'), {status: 503});
    return [artifact];
  }, {expectedId: 42, sleep: async () => {}}), artifact);
  let retried = false;
  await assert.rejects(waitForArtifact(async () => {
    throw Object.assign(new Error('Forbidden'), {status: 403});
  }, {expectedId: 42, sleep: async () => {retried = true;}}), /Forbidden/);
  assert.equal(retried, false);
});
