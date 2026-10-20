(function () {
  "use strict";
  var input = document.getElementById("search-input");
  var results = document.getElementById("search-results");
  var status = document.getElementById("search-status");
  if (!input || !results || !status) {
    return;
  }

  var index = [];
  var loaded = false;

  fetch("search-index.json")
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      index = data;
      loaded = true;
      if (input.value.trim()) {
        runSearch(input.value);
      }
    })
    .catch(function () {
      status.textContent = "検索データの読み込みに失敗しました。時間をおいて再度お試しください。";
    });

  function shortenExcerpt(text) {
    if (text.length > 160) {
      return text.slice(0, 160) + "…";
    }
    return text;
  }

  // HTML文字列の組み立て（innerHTML方式）は、属性値コンテキストへの埋め込みで
  // エスケープ漏れが起きやすい（image_urlに"が含まれると属性から脱出しうる）ため、
  // DOM API（createElement + プロパティ代入）でカードを組み立てる。
  function renderCard(entry) {
    var card = document.createElement("a");
    card.className = "card";
    card.href = entry.url;

    var thumb = document.createElement("div");
    thumb.className = entry.image_url ? "thumb" : "thumb no-image";
    if (entry.image_url) {
      var img = document.createElement("img");
      img.src = entry.image_url;
      img.alt = "";
      thumb.appendChild(img);
    }

    var body = document.createElement("div");
    body.className = "card-body";

    var title = document.createElement("div");
    title.className = "card-title";
    title.textContent = entry.title || "";

    var meta = document.createElement("div");
    meta.className = "card-meta";
    var sourceBadge = document.createElement("span");
    sourceBadge.className = "source-badge";
    sourceBadge.textContent = entry.source || "";
    var dateSpan = document.createElement("span");
    dateSpan.textContent = entry.date || "";
    meta.appendChild(sourceBadge);
    meta.appendChild(dateSpan);

    var excerpt = document.createElement("p");
    excerpt.className = "excerpt";
    excerpt.textContent = shortenExcerpt(entry.excerpt || "");

    body.appendChild(title);
    body.appendChild(meta);
    body.appendChild(excerpt);

    card.appendChild(thumb);
    card.appendChild(body);
    return card;
  }

  function runSearch(query) {
    results.innerHTML = "";
    var q = query.trim().toLowerCase();
    if (!q) {
      status.textContent = "";
      return;
    }
    var matched = index.filter(function (entry) {
      var title = (entry.title || "").toLowerCase();
      var body = (entry.excerpt || "").toLowerCase();
      return title.indexOf(q) !== -1 || body.indexOf(q) !== -1;
    });
    status.textContent = matched.length + "件見つかりました";
    matched.forEach(function (entry) {
      results.appendChild(renderCard(entry));
    });
  }

  input.addEventListener("input", function () {
    if (!loaded) {
      return;
    }
    runSearch(input.value);
  });
})();
