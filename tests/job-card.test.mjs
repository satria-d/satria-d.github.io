import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import {descriptionContent} from '../web/description.mjs';
import {relevanceScore} from '../web/model.mjs';

const dom = new JSDOM(await readFile(new URL('../web/index.html', import.meta.url), 'utf8'), {url:'https://example.test/'});
globalThis.document = dom.window.document;
globalThis.window = dom.window;
window.setInterval = () => 0;
const {card} = await import('../web/app.mjs');
const astra = {
  company:'PT Astra International Tbk', source:'LinkedIn',
  title:'TAF - Management Trainee for Operations Batch 29',
  url:'https://example.test/job/astra', location:'Jakarta, ID', employment:'FULL_TIME',
  postedAt:'2026-11-06', deadline:'2026-12-06', match:90, category:'MT / ODP',
  evidence:'<strong>Deskripsi Pekerjaan<br><br></strong><ul><li>Program Management Trainee selama 9 sampai 12 bulan.</li><li>Mengikuti pelatihan komprehensif.<br><br></li></ul><strong>Persyaratan<br><br></strong><ul><li>Pendidikan minimal S1 dari semua jurusan dengan IPK minimal 3,50.</li><li>Terbuka bagi fresh graduate maupun kandidat dengan pengalaman kerja maksimal 2 tahun.</li></ul>',
};
test('Astra description has headings and list items, and score is visible without opening details', () => {
  const node = card(astra), details = node.querySelector('details');
  assert.equal(details.open, false);
  assert.equal(node.querySelector('.job-meta').firstElementChild.className,'job-relevance');
  assert.match(node.querySelector('.job-relevance').textContent,/Relevansi bidang90\/100/);
  assert.equal(node.querySelector('.job-relevance').closest('details'),null);
  assert.equal(details.querySelectorAll('li').length,4);
  assert.equal(details.querySelectorAll('.evidence-body strong').length,2);
  assert.match(details.textContent,/IPK minimal 3,50/);
  assert.doesNotMatch(details.textContent,/<\/?(?:strong|ul|li|br)\b/);
});
test('Source markup cannot introduce scripts, handlers, resources, styles or links', () => {
  const body = document.createElement('div');
  body.append(descriptionContent('<p onclick="alert(1)" style="position:fixed">Fresh graduate &amp; Excel</p><script>alert(1)</script><img src="https://example.test/tracker" onerror="alert(1)"><svg onload="alert(1)"><script>bad</script></svg><iframe src="https://example.test"></iframe><a href="javascript:alert(1)">Baca syarat</a><ul><li data-x="x">IPK &gt;= 3.50</li></ul>'));
  assert.equal(body.querySelector('script,img,svg,iframe,a,style'),null);
  assert.equal(body.querySelector('[onclick],[onerror],[onload],[style],[src],[href],[data-x]'),null);
  assert.match(body.textContent,/Fresh graduate & Excel/);
  assert.match(body.textContent,/Baca syarat/);
  assert.match(body.textContent,/IPK >= 3.50/);
  assert.doesNotMatch(body.textContent,/alert\(1\)|bad/);
});
test('Plain text and escaped HTML both remain readable', () => {
  for (const source of ['&lt;strong&gt;Persyaratan&lt;/strong&gt;&lt;ul&gt;&lt;li&gt;S1 Matematika&lt;/li&gt;&lt;/ul&gt;', '&amp;lt;strong&amp;gt;Persyaratan&amp;lt;/strong&amp;gt;', '<p>&lt;strong&gt;Persyaratan&lt;/strong&gt;</p>']) {
    const body=document.createElement('div');body.append(descriptionContent(source));
    assert.match(body.textContent,/Persyaratan/);assert.doesNotMatch(body.textContent,/<strong>|&lt;/);
    assert.ok(body.querySelector('strong'));
  }
  const source='Fresh graduate\nPengalaman 0–2 tahun\nExcel & Power Query';
  assert.equal(descriptionContent(source).textContent,source);
});
test('Missing or invalid relevance scores are not displayed as zero or NaN', () => {
  for (const value of [null,undefined,'', ' ', true, [], {}, NaN, Infinity, -1, 101]) {
    assert.equal(relevanceScore(value),null);
    assert.match(card({...astra,match:value}).querySelector('.job-relevance').textContent,/Belum tersedia/);
  }
  assert.equal(relevanceScore('90'),90);
  assert.equal(relevanceScore(0),0);
  assert.match(card({...astra,match:0}).querySelector('.job-relevance').textContent,/0\/100/);
});
