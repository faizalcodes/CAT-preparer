document.addEventListener("DOMContentLoaded", () => {
  const popup = document.getElementById("wordPopup");
  if (!popup) return; // not on the article page

  const popupWord = document.getElementById("popupWord");
  const popupMeaning = document.getElementById("popupMeaning");
  const popupExample = document.getElementById("popupExample");
  const closeBtn = document.getElementById("wordPopupClose");
  const articleContent = document.querySelector(".article-content");

  // build a lookup from the word bank list items in the sidebar
  const dictionary = {};
  document.querySelectorAll(".word-item").forEach((el) => {
    dictionary[el.dataset.word.toLowerCase()] = {
      word: el.dataset.word,
      meaning: el.dataset.meaning,
      example: el.dataset.example,
    };
    el.addEventListener("click", () => openPopup(el.dataset.word));
  });

  document.querySelectorAll(".vocab-word").forEach((el) => {
    el.addEventListener("click", () => openPopup(el.dataset.word));
  });

  articleContent?.addEventListener("dblclick", () => {
    const selection = window.getSelection();
    const word = selection.toString().trim();
    if (!word || /\s/.test(word)) return;

    let context = "";
    const anchorNode = selection.anchorNode;
    if (anchorNode && anchorNode.parentElement) {
      context = anchorNode.parentElement.textContent.trim().slice(0, 300);
    }
    openPopupAsync(word, context);
  });

  function openPopup(word) {
    const entry = dictionary[word.toLowerCase()];
    if (!entry) return;
    renderPopup(entry.word, entry.meaning, entry.example);
  }

  async function openPopupAsync(word, context) {
    const cached = dictionary[word.toLowerCase()];
    if (cached) {
      renderPopup(cached.word, cached.meaning, cached.example);
      return;
    }
    renderPopup(word, "Looking up…", "");
    popup.classList.add("open");
    try {
      const resp = await fetch("/api/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word, context }),
      });
      const data = await resp.json();
      if (!resp.ok || data.error) {
        renderPopup(word, "Couldn't fetch a definition. Try again.", "");
        return;
      }
      dictionary[word.toLowerCase()] = data;
      renderPopup(data.word || word, data.meaning || "", data.example || "");
    } catch (err) {
      renderPopup(word, "Network error — check your connection.", "");
    }
  }

  function renderPopup(word, meaning, example) {
    popupWord.textContent = word;
    popupMeaning.textContent = meaning;
    popupExample.textContent = example ? `"${example}"` : "";
    popup.classList.add("open");
  }

  closeBtn.addEventListener("click", () => popup.classList.remove("open"));
  popup.addEventListener("click", (e) => { if (e.target === popup) popup.classList.remove("open"); });

  // ---------- Quiz ----------
  const quizModal = document.getElementById("quizModal");
  const quizModalClose = document.getElementById("quizModalClose");
  const quizBody = document.getElementById("quizBody");
  const startQuizBtn = document.getElementById("startQuizBtn");
  const startSingleQuizBtn = document.getElementById("startSingleQuizBtn");

  const wordPickerModal = document.getElementById("wordPickerModal");
  const wordPickerClose = document.getElementById("wordPickerClose");
  const wordPickerList = document.getElementById("wordPickerList");

  let quizState = { questions: [], index: 0, score: 0 };

  startQuizBtn?.addEventListener("click", () => startQuiz(Object.values(dictionary)));

  startSingleQuizBtn?.addEventListener("click", () => {
    const words = Object.values(dictionary);
    if (words.length === 0) { alert("No vocab words found for this article yet."); return; }
    wordPickerList.innerHTML = "";
    words.forEach((w) => {
      const li = document.createElement("li");
      li.className = "word-picker-item";
      li.textContent = w.word;
      li.addEventListener("click", () => {
        wordPickerModal.classList.remove("open");
        startQuiz([w]);
      });
      wordPickerList.appendChild(li);
    });
    wordPickerModal.classList.add("open");
  });

  wordPickerClose?.addEventListener("click", () => wordPickerModal.classList.remove("open"));
  wordPickerModal?.addEventListener("click", (e) => { if (e.target === wordPickerModal) wordPickerModal.classList.remove("open"); });

  async function startQuiz(words) {
    if (!words.length) { alert("No vocab words found for this article yet."); return; }

    quizModal.classList.add("open");
    quizBody.innerHTML = `<div class="quiz-loading"><div class="spinner"></div><p>Cooking up some questions…</p></div>`;

    try {
      const resp = await fetch("/api/quiz/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ words }),
      });
      const data = await resp.json();
      if (!resp.ok || data.error || !data.questions?.length) {
        quizBody.innerHTML = `<p class="quiz-loading">Couldn't generate questions. Try again.</p>`;
        return;
      }
      quizState = { questions: data.questions, index: 0, score: 0 };
      renderQuestion();
    } catch (err) {
      quizBody.innerHTML = `<p class="quiz-loading">Network error — try again.</p>`;
    }
  }

  function renderQuestion() {
    const q = quizState.questions[quizState.index];
    if (!q) { renderQuizComplete(); return; }

    quizBody.innerHTML = `
      <p class="quiz-progress">Question ${quizState.index + 1} of ${quizState.questions.length}</p>
      <p class="quiz-prompt">${q.prompt}</p>
      <input type="text" id="quizAnswerInput" class="quiz-answer-input"
             placeholder="${q.type === "fill_blank" ? "Type the missing word" : "Write your sentence"}"
             autocomplete="off" />
      <button id="quizSubmitBtn" class="quiz-submit-btn">Submit</button>
      <p id="quizFeedback" class="quiz-feedback"></p>
    `;

    const input = document.getElementById("quizAnswerInput");
    input.focus();
    document.getElementById("quizSubmitBtn").addEventListener("click", submitAnswer);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") submitAnswer(); });
  }

  async function submitAnswer() {
    const q = quizState.questions[quizState.index];
    const input = document.getElementById("quizAnswerInput");
    const feedbackEl = document.getElementById("quizFeedback");
    const submitBtn = document.getElementById("quizSubmitBtn");
    const answer = input.value.trim();
    if (!answer) return;

    submitBtn.disabled = true;
    input.disabled = true;

    if (q.type === "fill_blank") {
      const isCorrect = answer.toLowerCase() === q.word.toLowerCase();
      feedbackEl.textContent = isCorrect ? "✔ Correct!" : `✘ Not quite — the word was "${q.word}".`;
      feedbackEl.className = "quiz-feedback " + (isCorrect ? "correct" : "incorrect");
      if (isCorrect) quizState.score++;
      setTimeout(nextQuestion, 1400);
    } else {
      feedbackEl.innerHTML = `<div class="spinner" style="width:24px;height:24px;margin:6px auto;"></div>`;
      try {
        const resp = await fetch("/api/quiz/check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ word: q.word, meaning: q.meaning, sentence: answer }),
        });
        const data = await resp.json();
        if (!resp.ok || data.error) {
          feedbackEl.textContent = "Couldn't check that — moving on.";
        } else {
          feedbackEl.textContent = (data.correct ? "✔ " : "✘ ") + data.feedback;
          feedbackEl.className = "quiz-feedback " + (data.correct ? "correct" : "incorrect");
          if (data.correct) quizState.score++;
        }
      } catch (err) {
        feedbackEl.textContent = "Network error — moving on.";
      }
      setTimeout(nextQuestion, 2200);
    }
  }

  function nextQuestion() {
    quizState.index++;
    renderQuestion();
  }

  function getRank(percent) {
    if (percent === 100) return { emoji: "🏆", label: "Word Wizard", feedback: "Perfect score! These words are locked in for good." };
    if (percent >= 80) return { emoji: "🌟", label: "Sharp Reader", feedback: "Excellent work — just a couple of words to revisit." };
    if (percent >= 50) return { emoji: "🌱", label: "Growing Strong", feedback: "Good progress! Try the single-word practice on the ones you missed." };
    return { emoji: "📚", label: "Keep Practicing", feedback: "No worries — re-read the word bank and try again in a bit." };
  }

  function renderQuizComplete() {
    const total = quizState.questions.length;
    const percent = Math.round((quizState.score / total) * 100);
    const rank = getRank(percent);

    quizBody.innerHTML = `
      <p class="quiz-complete-title">Quiz complete!</p>
      <span class="quiz-rank-badge">${rank.emoji}</span>
      <p class="quiz-rank-label">${rank.label}</p>
      <p class="quiz-score">You scored ${quizState.score} / ${total} (${percent}%)</p>
      <p class="quiz-rank-feedback">${rank.feedback}</p>
      <div class="quiz-result-actions">
        <button id="quizRetryBtn" class="quiz-submit-btn">Try again</button>
        <button id="quizCloseFinalBtn" class="quiz-start-btn quiz-start-btn--secondary">Close</button>
      </div>
    `;
    document.getElementById("quizCloseFinalBtn").addEventListener("click", () => quizModal.classList.remove("open"));
    document.getElementById("quizRetryBtn").addEventListener("click", () => startQuiz(Object.values(dictionary)));
  }

  quizModalClose?.addEventListener("click", () => quizModal.classList.remove("open"));
  quizModal?.addEventListener("click", (e) => { if (e.target === quizModal) quizModal.classList.remove("open"); });

  // ---------- reading flower (follows scroll progress down the article) ----------
  const flower = document.getElementById("readingFlower");
  if (flower) {
    const minTop = 100;
    const maxTop = window.innerHeight - 120;

    window.addEventListener("scroll", () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const percent = docHeight > 0 ? Math.min(scrollTop / docHeight, 1) : 0;
      flower.style.top = `${minTop + percent * (maxTop - minTop)}px`;
    });
  }
});