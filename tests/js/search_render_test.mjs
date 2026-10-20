// static/search.js の renderCard が、属性値コンテキストから脱出できる文字列
// （image_url中の `"` 等）を与えられても、新しい要素や属性を注入できないことを
// 確認する最小テスト。
//
// jsdom等の外部依存を使わず、renderCardが実際に呼び出すDOM APIの範囲だけを
// 素朴なオブジェクトで模したフェイクDOMの上で、static/search.jsのソースを
// そのまま（書き換えずに）実行する。
//
// 実行方法: node tests/js/search_render_test.mjs
// （tests/test_search_js_xss.py からもサブプロセスとして呼び出される）

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import assert from "node:assert/strict";

const here = path.dirname(fileURLToPath(import.meta.url));
const searchJsPath = path.join(here, "..", "..", "static", "search.js");
const code = readFileSync(searchJsPath, "utf8");

class FakeElement {
  constructor(tagName) {
    this.tagName = String(tagName).toUpperCase();
    this.children = [];
    this._className = "";
    this._textContent = "";
    this._listeners = {};
  }
  set className(v) {
    this._className = v;
  }
  get className() {
    return this._className;
  }
  set textContent(v) {
    this._textContent = v;
    // textContentへの代入は子要素を全て置き換える（実DOMと同じ挙動）。
    this.children = [];
  }
  get textContent() {
    return this._textContent;
  }
  set innerHTML(v) {
    if (v !== "") {
      throw new Error(
        "このフェイクDOMはinnerHTMLへの空文字以外の代入を想定していません: " + v
      );
    }
    this.children = [];
  }
  appendChild(child) {
    this.children.push(child);
    return child;
  }
  addEventListener(type, handler) {
    this._listeners[type] = handler;
  }
}

const inputEl = new FakeElement("input");
inputEl.value = "";
const resultsEl = new FakeElement("div");
const statusEl = new FakeElement("div");

const elementsById = {
  "search-input": inputEl,
  "search-results": resultsEl,
  "search-status": statusEl,
};

globalThis.document = {
  getElementById(id) {
    return elementsById[id] || null;
  },
  createElement(tag) {
    return new FakeElement(tag);
  },
};

const maliciousImageUrl = 'https://evil.example.com/x.jpg" onerror="alert(1)';
const maliciousTitle = 'テスト記事<script>alert(1)</script>';
const maliciousSource = 'Test"Source';
const maliciousExcerpt = 'サンプル本文 "quote" <tag>注入テスト';

const fakeIndex = [
  {
    title: maliciousTitle,
    url: "https://example.com/a",
    source: maliciousSource,
    date: "2026-10-20",
    excerpt: maliciousExcerpt,
    image_url: maliciousImageUrl,
  },
];

globalThis.fetch = function fetchStub() {
  return Promise.resolve({
    json: () => Promise.resolve(fakeIndex),
  });
};

// search.jsのIIFEを素のevalで（グローバルスコープで）そのまま実行する。
(0, eval)(code);

// fetch().then().then()の非同期解決を待つ（マイクロタスクを使い切ってから
// マクロタスクで1つ区切りを入れる）。
await new Promise((resolve) => setImmediate(resolve));
await new Promise((resolve) => setImmediate(resolve));

assert.ok(
  typeof inputEl._listeners.input === "function",
  "input要素にinputイベントリスナーが登録されていること"
);

inputEl.value = "テスト";
inputEl._listeners.input();

assert.equal(resultsEl.children.length, 1, "検索結果が1件描画されること");

const card = resultsEl.children[0];
assert.equal(card.tagName, "A");
assert.equal(card.children.length, 2, "カードはthumbとcard-bodyの2要素を持つこと");

const [thumb, body] = card.children;

// --- image_url の属性脱出防止 ---
assert.equal(thumb.children.length, 1, "thumb内にimg要素が1つだけ生成されること");
const img = thumb.children[0];
assert.equal(img.tagName, "IMG");
assert.equal(
  img.src,
  maliciousImageUrl,
  "image_urlが加工されずそのままsrcプロパティに入ること（文字列結合によるHTML組み立てをしていない証拠）"
);
assert.equal(img.alt, "");
assert.ok(
  !("onerror" in img),
  "image_url中の文字列からonerror等の属性が注入されていないこと"
);
assert.equal(
  Object.prototype.hasOwnProperty.call(img, "src"),
  true
);

// --- title / source / excerpt のテキスト注入防止（textContent方式） ---
const titleEl = body.children[0];
assert.equal(titleEl.textContent, maliciousTitle);
assert.equal(
  titleEl.children.length,
  0,
  "<script>等のタグ文字列が子要素として解釈されていないこと（textContentで挿入されている証拠）"
);

const metaEl = body.children[1];
const sourceBadgeEl = metaEl.children[0];
assert.equal(sourceBadgeEl.textContent, maliciousSource);
assert.equal(sourceBadgeEl.children.length, 0);

const excerptEl = body.children[2];
assert.ok(excerptEl.textContent.includes('"quote"'));
assert.equal(excerptEl.children.length, 0);

console.log("OK: search.js renderCard escaping/XSS regression test passed");
