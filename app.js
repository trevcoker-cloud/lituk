(function () {
  'use strict';

  var TESTS = window.LITUK_TESTS || [];
  var S = window.LITUK;
  var GROUPS = ['All'];

  var state = { test: null, index: 0, answers: {}, deadline: 0, tick: null, submitted: false, startedAt: 0 };
  var currentResult = null;
  var shareLink = '';
  var activeGroup = 'All';

  function $(id) { return document.getElementById(id); }

  function show(name) {
    ['study', 'home', 'quiz', 'result'].forEach(function (key) {
      var screen = $('screen-' + key);
      if (screen) screen.classList.toggle('is-active', key === name);
    });

    var onStudy = name === 'study';
    var navStudy = $('nav-study');
    var navTests = $('nav-tests');
    if (navStudy) navStudy.classList.toggle('is-current', onStudy);
    if (navTests) navTests.classList.toggle('is-current', !onStudy);

    window.scrollTo(0, 0);
  }

  function setUrl(query) {
    try {
      history.replaceState({}, '', location.pathname + query);
    } catch (err) { /* file:// or sandboxed preview */ }
  }

  /* ------------------------------------------------------------------ home */

  function buildGroups() {
    TESTS.forEach(function (test) {
      if (GROUPS.indexOf(test.group) === -1) GROUPS.push(test.group);
    });
    GROUPS.sort(function (a, b) {
      if (a === 'All') return -1;
      if (b === 'All') return 1;
      if (a === 'Full tests') return -1;
      if (b === 'Full tests') return 1;
      return a.localeCompare(b, undefined, { numeric: true });
    });
  }

  function renderFilters() {
    var wrap = $('filters');
    wrap.innerHTML = '';
    GROUPS.forEach(function (group) {
      var count = group === 'All' ? TESTS.length : TESTS.filter(function (t) { return t.group === group; }).length;
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip' + (group === activeGroup ? ' is-active' : '');
      chip.textContent = group + ' (' + count + ')';
      chip.setAttribute('aria-pressed', group === activeGroup ? 'true' : 'false');
      chip.addEventListener('click', function () {
        activeGroup = group;
        renderFilters();
        renderTests();
      });
      wrap.appendChild(chip);
    });
  }

  function renderTests() {
    var grid = $('test-grid');
    grid.innerHTML = '';
    var visible = TESTS.filter(function (test) {
      return activeGroup === 'All' || test.group === activeGroup;
    });

    visible.forEach(function (test) {
      var card = document.createElement('button');
      card.type = 'button';
      card.className = 'test-card';
      card.innerHTML =
        '<h3></h3>' +
        '<span class="test-meta">' + test.questions.length + ' questions · 45 min</span>' +
        '<span class="test-meta"></span>' +
        '<span class="test-go">Start test →</span>';
      card.querySelector('h3').textContent = test.name;
      card.querySelectorAll('.test-meta')[1].textContent = test.group;
      card.addEventListener('click', function () { startTest(test); });
      grid.appendChild(card);
    });

    $('catalogue-note').textContent = visible.length + ' tests · ' +
      visible.reduce(function (sum, test) { return sum + test.questions.length; }, 0).toLocaleString('en-GB') +
      ' questions';
  }

  function renderHeroStats() {
    var questions = TESTS.reduce(function (sum, test) { return sum + test.questions.length; }, 0);
    var chapters = (window.LITUK_STUDY || []).length;

    ['stat-tests', 'stat-tests-2'].forEach(function (id) {
      if ($(id)) $(id).textContent = TESTS.length;
    });
    ['stat-questions', 'stat-questions-2'].forEach(function (id) {
      if ($(id)) $(id).textContent = questions.toLocaleString('en-GB');
    });
    if ($('stat-chapters')) $('stat-chapters').textContent = chapters;
    $('header-meta').textContent = TESTS.length + ' practice tests · 2026 edition';
  }

  function renderShared() {
    var shared = S.parseShared(location.search);
    if (!shared) return;
    var test = TESTS.filter(function (t) { return t.id === shared.testId; })[0];
    if (!test) return;

    $('shared-score').textContent = shared.score + '/' + shared.total;
    $('shared-percent').textContent = shared.percent + '%';
    $('shared-line').textContent = 'on ' + test.name + ' · ' +
      (shared.secondsUsed ? 'finished in ' + S.formatTime(shared.secondsUsed) : 'no time recorded');
    var badge = $('shared-badge');
    badge.textContent = shared.passed ? 'Pass' : 'Not passed';
    badge.classList.toggle('is-fail', !shared.passed);
    $('shared-cta').textContent = 'Take ' + test.name + ' yourself and see if you beat ' + shared.score + '/24.';
    $('shared-start').textContent = 'Take ' + test.name;
    $('shared-start').onclick = function () { startTest(test); };
    $('shared-card').hidden = false;
    show('home');
  }

  /* ----------------------------------------------------------------- study */

  var CHAPTER_GROUP = {
    1: 'Chapters 1\u20132',
    2: 'Chapters 1\u20132',
    3: 'Chapter 3',
    4: 'Chapter 4',
    5: 'Chapter 5'
  };

  function studyBlocks(chapter) {
    var blocks = chapter.blocks || [];
    if (blocks.length && blocks[0].t === 'p' && chapter.summary &&
        chapter.summary.indexOf(blocks[0].x.slice(0, 50)) === 0) {
      return blocks.slice(1);
    }
    return blocks;
  }

  function renderStudy() {
    var study = window.LITUK_STUDY || [];
    var list = $('study-list');
    if (!list) return;
    list.innerHTML = '';
    $('study-note').textContent = study.length + ' chapters · revision notes';

    study.forEach(function (chapter) {
      var card = document.createElement('article');
      card.className = 'study-card';
      card.id = chapter.id;

      var head = document.createElement('div');
      head.className = 'study-card-head';

      var number = document.createElement('p');
      number.className = 'study-num';
      number.textContent = 'Chapter ' + chapter.number;

      var body = document.createElement('div');
      body.className = 'study-body';

      var title = document.createElement('h3');
      title.className = 'study-title';
      title.textContent = chapter.title;

      var summary = document.createElement('p');
      summary.className = 'study-summary';
      summary.textContent = chapter.summary;

      var blocks = studyBlocks(chapter);
      var notes = blocks.filter(function (block) {
        return block.t === 'p' || block.t === 'ul';
      }).length;

      var meta = document.createElement('p');
      meta.className = 'study-meta';
      meta.textContent = notes + ' notes in this chapter';

      body.appendChild(title);
      body.appendChild(summary);
      body.appendChild(meta);
      head.appendChild(number);
      head.appendChild(body);

      var actions = document.createElement('div');
      actions.className = 'study-actions';

      var toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'btn btn-ghost';
      toggle.textContent = 'Read the notes';
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-controls', chapter.id + '-notes');

      var practise = document.createElement('button');
      practise.type = 'button';
      practise.className = 'btn btn-primary';
      practise.textContent = 'Practise this chapter';

      actions.appendChild(toggle);
      actions.appendChild(practise);

      var panel = document.createElement('div');
      panel.className = 'study-notes';
      panel.id = chapter.id + '-notes';
      panel.hidden = true;
      renderNotes(panel, blocks);
      renderQuickCheck(panel, chapter);

      toggle.addEventListener('click', function () { toggleNotes(card, toggle, panel); });
      practise.addEventListener('click', function () {
        openTests(CHAPTER_GROUP[chapter.number] || 'All');
      });

      card.appendChild(head);
      card.appendChild(actions);
      card.appendChild(panel);
      list.appendChild(card);
    });
  }

  function renderNotes(container, blocks) {
    blocks.forEach(function (block) {
      var node;
      if (block.t === 'h2') {
        node = document.createElement('h4');
        node.textContent = block.x;
      } else if (block.t === 'h3') {
        node = document.createElement('h5');
        node.textContent = block.x;
      } else if (block.t === 'ul') {
        node = document.createElement('ul');
        block.x.forEach(function (item) {
          var li = document.createElement('li');
          li.textContent = item;
          node.appendChild(li);
        });
      } else {
        node = document.createElement('p');
        node.textContent = block.x;
      }
      container.appendChild(node);
    });
  }

  function chapterPool(chapter) {
    var group = CHAPTER_GROUP[chapter.number];
    var seen = {};
    var pool = [];

    TESTS.forEach(function (test) {
      if (test.group !== group) return;
      test.questions.forEach(function (question) {
        var key = question.q.toLowerCase();
        if (seen[key]) return;
        seen[key] = true;
        pool.push(question);
      });
    });

    return pool;
  }

  function renderQuickCheck(container, chapter) {
    var pool = chapterPool(chapter);
    if (pool.length < 5) return;

    var wrap = document.createElement('section');
    wrap.className = 'quick';
    wrap.setAttribute('aria-label', 'Quick check');

    var head = document.createElement('div');
    head.className = 'quick-head';

    var title = document.createElement('h4');
    title.textContent = 'Quick check';

    var score = document.createElement('p');
    score.className = 'quick-score';
    score.setAttribute('aria-live', 'polite');

    head.appendChild(title);
    head.appendChild(score);

    var list = document.createElement('ol');
    list.className = 'quick-list';

    var again = document.createElement('button');
    again.type = 'button';
    again.className = 'btn btn-ghost';
    again.textContent = 'Try another five';

    var current = { questions: [], answered: 0, correct: 0 };

    function pick() {
      var copy = pool.slice();
      var chosen = [];
      while (copy.length && chosen.length < 5) {
        chosen.push(copy.splice(Math.floor(Math.random() * copy.length), 1)[0]);
      }
      return chosen;
    }

    function setScore() {
      score.textContent = current.answered
        ? current.correct + ' of ' + current.questions.length + ' correct'
        : current.questions.length + ' questions · one at a time';
    }

    function build() {
      current.questions = pick();
      current.answered = 0;
      current.correct = 0;
      list.innerHTML = '';
      current.questions.forEach(function (question, index) {
        list.appendChild(buildQuickItem(question, index, current, setScore));
      });
      setScore();
    }

    again.addEventListener('click', build);

    wrap.appendChild(head);
    wrap.appendChild(list);
    wrap.appendChild(again);
    container.appendChild(wrap);
    build();
  }

  function buildQuickItem(question, index, current, setScore) {
    var multi = question.a.length > 1;
    var chosen = [];
    var done = false;

    var item = document.createElement('li');
    item.className = 'quick-item';

    var prompt = document.createElement('p');
    prompt.className = 'quick-q';
    prompt.textContent = (index + 1) + '. ' + question.q;

    if (multi) {
      var tag = document.createElement('span');
      tag.className = 'quick-tag';
      tag.textContent = 'Select ' + question.a.length;
      prompt.appendChild(tag);
    }

    var options = document.createElement('div');
    options.className = 'quick-options';
    var buttons = [];

    var feedback = document.createElement('p');
    feedback.className = 'quick-feedback';
    feedback.hidden = true;

    var check = document.createElement('button');
    check.type = 'button';
    check.className = 'btn btn-ghost btn-sm';
    check.textContent = 'Check answer';
    check.disabled = true;

    function paint() {
      buttons.forEach(function (button, position) {
        var on = chosen.indexOf(position) !== -1;
        button.classList.toggle('is-selected', on);
        button.setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      check.disabled = chosen.length === 0 || done;
    }

    function answerLetters() {
      return question.a.map(function (position) { return String.fromCharCode(65 + position); }).join(' and ');
    }

    function evaluate() {
      if (done || !chosen.length) return;
      done = true;

      var right = S.sameSet(chosen, question.a);
      buttons.forEach(function (button, position) {
        if (question.a.indexOf(position) !== -1) button.classList.add('is-right');
        else if (chosen.indexOf(position) !== -1) button.classList.add('is-wrong');
        button.disabled = true;
      });

      var verdict = right ? 'Correct.' : 'Not quite — the answer is ' + answerLetters() + '.';
      feedback.textContent = question.e ? verdict + ' ' + question.e : verdict;
      feedback.className = 'quick-feedback ' + (right ? 'is-right' : 'is-wrong');
      feedback.hidden = false;

      check.hidden = true;
      current.answered++;
      if (right) current.correct++;
      setScore();
    }

    question.o.forEach(function (label, position) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'option option-sm';
      button.setAttribute('aria-pressed', 'false');

      var key = document.createElement('span');
      key.className = 'option-key';
      key.textContent = String.fromCharCode(65 + position);

      var text = document.createElement('span');
      text.className = 'option-text';
      text.textContent = label;

      button.appendChild(key);
      button.appendChild(text);

      button.addEventListener('click', function () {
        if (done) return;
        if (multi) {
          var at = chosen.indexOf(position);
          if (at === -1) chosen.push(position); else chosen.splice(at, 1);
          chosen.sort(function (a, b) { return a - b; });
          paint();
        } else {
          chosen = [position];
          paint();
          evaluate();
        }
      });

      buttons.push(button);
      options.appendChild(button);
    });

    check.addEventListener('click', evaluate);

    item.appendChild(prompt);
    item.appendChild(options);
    if (multi) item.appendChild(check);
    item.appendChild(feedback);
    paint();

    return item;
  }

  function toggleNotes(card, button, panel) {
    var opening = panel.hidden;
    panel.hidden = !opening;
    button.textContent = opening ? 'Hide the notes' : 'Read the notes';
    button.setAttribute('aria-expanded', opening ? 'true' : 'false');

    if (!opening) return;
    document.querySelectorAll('.study-card').forEach(function (other) {
      if (other === card) return;
      var otherPanel = other.querySelector('.study-notes');
      var otherButton = other.querySelector('.study-actions .btn-ghost');
      if (otherPanel && !otherPanel.hidden) {
        otherPanel.hidden = true;
        otherButton.textContent = 'Read the notes';
        otherButton.setAttribute('aria-expanded', 'false');
      }
    });
  }

  function openTests(group) {
    activeGroup = group || 'All';
    renderFilters();
    renderTests();
    show('home');
    var grid = $('test-grid');
    if (grid) grid.scrollIntoView({ block: 'start' });
  }

  function leaveQuiz(target, resetFilter) {
    if ($('screen-quiz').classList.contains('is-active') && !state.submitted) {
      if (!window.confirm('Leave this test? Your answers will be lost.')) return;
    }
    clearInterval(state.tick);
    if (target === 'study') {
      show('study');
      return;
    }
    if (resetFilter) activeGroup = 'All';
    renderFilters();
    renderTests();
    show('home');
  }

  /* ------------------------------------------------------------------ quiz */

  function startTest(test) {
    clearInterval(state.tick);
    state = {
      test: test,
      index: 0,
      answers: {},
      deadline: Date.now() + S.SECONDS * 1000,
      tick: null,
      submitted: false,
      startedAt: Date.now()
    };
    currentResult = null;
    setUrl('');

    $('quiz-title').textContent = test.name;
    $('screen-quiz').setAttribute('aria-labelledby', 'quiz-title');
    show('quiz');
    renderQuestion();
    renderGrid();
    resetSubmitPrompt();

    state.tick = setInterval(tickTimer, 250);
    tickTimer();
  }

  function tickTimer() {
    var left = Math.max(0, Math.round((state.deadline - Date.now()) / 1000));
    var timer = $('timer');
    timer.textContent = S.formatTime(left);
    timer.classList.toggle('is-urgent', left <= 300);
    if (left <= 0) {
      clearInterval(state.tick);
      finish(true);
    }
  }

  function currentQuestion() {
    return state.test.questions[state.index];
  }

  function renderQuestion() {
    var question = currentQuestion();
    var total = state.test.questions.length;
    var chosen = state.answers[state.index] || [];
    var multi = question.a.length > 1;

    $('q-chapter').textContent = state.test.name;
    $('q-text').textContent = question.q;

    var hint = $('q-hint');
    hint.textContent = multi ? 'Select ' + question.a.length + ' answers.' : 'Select 1 answer.';
    hint.hidden = false;

    var options = $('options');
    options.innerHTML = '';
    question.o.forEach(function (label, position) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'option' + (chosen.indexOf(position) !== -1 ? ' is-selected' : '');
      button.setAttribute('aria-pressed', chosen.indexOf(position) !== -1 ? 'true' : 'false');

      var key = document.createElement('span');
      key.className = 'option-key';
      key.textContent = String.fromCharCode(65 + position);
      var text = document.createElement('span');
      text.className = 'option-text';
      text.textContent = label;

      button.appendChild(key);
      button.appendChild(text);
      button.addEventListener('click', function () { choose(position); });
      options.appendChild(button);
    });

    $('progress-text').textContent = 'Question ' + (state.index + 1) + ' of ' + total;
    $('progress-fill').style.width = ((state.index + 1) / total * 100) + '%';
    var bar = $('progress-fill').parentElement;
    bar.setAttribute('aria-valuenow', String(state.index + 1));
    bar.setAttribute('aria-valuemax', String(total));

    $('btn-prev').disabled = state.index === 0;
    $('btn-next').textContent = state.index === total - 1 ? 'Review answers' : 'Next question';
  }

  function choose(position) {
    var question = currentQuestion();
    var multi = question.a.length > 1;
    var chosen = (state.answers[state.index] || []).slice();

    if (multi) {
      var at = chosen.indexOf(position);
      if (at === -1) chosen.push(position); else chosen.splice(at, 1);
      chosen.sort(function (a, b) { return a - b; });
      if (chosen.length) state.answers[state.index] = chosen;
      else delete state.answers[state.index];
    } else {
      state.answers[state.index] = [position];
    }

    renderQuestion();
    renderGrid();
    resetSubmitPrompt();

    if (!multi && state.index < state.test.questions.length - 1) {
      var from = state.index;
      setTimeout(function () {
        if (state.submitted || state.index !== from) return;
        if (state.answers[from]) goTo(from + 1);
      }, 170);
    }
  }

  function renderGrid() {
    var grid = $('q-grid');
    grid.innerHTML = '';
    state.test.questions.forEach(function (_, index) {
      var dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'q-dot' +
        (state.answers[index] && state.answers[index].length ? ' is-answered' : '') +
        (index === state.index ? ' is-current' : '');
      dot.textContent = index + 1;
      dot.setAttribute('aria-label', 'Question ' + (index + 1) +
        (state.answers[index] && state.answers[index].length ? ', answered' : ', not answered'));
      dot.setAttribute('aria-current', index === state.index ? 'true' : 'false');
      dot.addEventListener('click', function () { goTo(index); });
      grid.appendChild(dot);
    });
  }

  function goTo(index) {
    if (index < 0 || index >= state.test.questions.length) return;
    state.index = index;
    renderQuestion();
    renderGrid();
    resetSubmitPrompt();
    var card = document.querySelector('.question-card');
    if (card && card.getBoundingClientRect().top < 0) card.scrollIntoView({ block: 'start' });
  }

  function resetSubmitPrompt() {
    var button = $('btn-submit');
    delete button.dataset.confirm;
    button.textContent = 'Finish & see score';
    $('submit-warn').hidden = true;
  }

  function finish(auto) {
    if (state.submitted) return;
    state.submitted = true;
    clearInterval(state.tick);

    var used = Math.round((Date.now() - state.startedAt) / 1000);
    used = Math.min(used, S.SECONDS);

    var result = S.grade(state.test.questions, state.answers);
    result.secondsUsed = used;
    result.autoSubmitted = !!auto;

    renderResult(result);
    show('result');
    setUrl('?t=' + encodeURIComponent(state.test.id) + '&s=' + result.score + '&d=' + used);
    currentResult = result;
  }

  /* ---------------------------------------------------------------- result */

  function renderResult(result) {
    var ring = $('score-ring');
    ring.style.setProperty('--pct', result.percent);
    ring.classList.toggle('is-fail', !result.passed);

    $('score-big').textContent = result.score;
    $('score-total').textContent = '/' + result.total;

    var title = result.passed ? 'You passed' : (result.score >= result.passMark - 2 ? 'So close' : 'Keep practising');
    $('result-title').textContent = title;

    var line = result.score + ' of ' + result.total + ' correct (' + result.percent + '%). ';
    line += result.passed
      ? 'That clears the ' + result.passMark + ' needed to pass ' + state.test.name + '.'
      : 'You needed ' + result.passMark + ' to pass ' + state.test.name + '.';
    if (result.autoSubmitted) line += ' Time ran out, so your answers were submitted automatically.';
    $('result-line').textContent = line;
    $('result-eyebrow').textContent = state.test.name + ' · result';

    renderStats(result);
    renderReview(result);

    shareLink = S.shareUrl(location.href.split('#')[0].split('?')[0], state.test.id, result);
    $('share-url').value = shareLink;
    $('copy-status').textContent = '';
  }

  function renderStats(result) {
    var stats = $('result-stats');
    stats.innerHTML = '';
    [
      [String(result.score), 'Correct'],
      [String(result.incorrect), 'Incorrect'],
      [String(result.unanswered), 'Not answered'],
      [S.formatTime(result.secondsUsed) + ' / 45:00', 'Time used']
    ].forEach(function (pair) {
      var card = document.createElement('div');
      card.className = 'stat';
      var value = document.createElement('strong');
      value.textContent = pair[0];
      var label = document.createElement('span');
      label.textContent = pair[1];
      card.appendChild(value);
      card.appendChild(label);
      stats.appendChild(card);
    });
  }

  function renderReview(result) {
    var list = $('review');
    list.innerHTML = '';

    result.results.forEach(function (entry, index) {
      var question = state.test.questions[index];
      var item = document.createElement('li');
      item.className = 'review-item' + (entry.correct ? '' : entry.answered ? ' is-wrong' : ' is-skipped');

      var head = document.createElement('div');
      head.className = 'review-q';

      var number = document.createElement('span');
      number.className = 'review-num';
      number.textContent = (index + 1) + '.';

      var text = document.createElement('span');
      text.textContent = question.q;

      var status = document.createElement('span');
      status.className = 'review-status';
      status.textContent = entry.correct ? 'Correct' : entry.answered ? 'Incorrect' : 'Not answered';

      head.appendChild(number);
      head.appendChild(text);
      head.appendChild(status);

      var options = document.createElement('ul');
      options.className = 'review-options';
      question.o.forEach(function (label, position) {
        var option = document.createElement('li');
        var isAnswer = question.a.indexOf(position) !== -1;
        var isChosen = entry.chosen.indexOf(position) !== -1;
        if (isAnswer) option.className = 'is-correct';
        else if (isChosen) option.className = 'is-chosen-wrong';
        option.appendChild(document.createTextNode(label));
        options.appendChild(option);
      });

      item.appendChild(head);
      item.appendChild(options);

      if (question.e) {
        var explain = document.createElement('p');
        explain.className = 'review-explain';
        explain.textContent = question.e;
        item.appendChild(explain);
      }

      list.appendChild(item);
    });
  }

  /* ----------------------------------------------------------------- share */

  function fallbackCopy(value) {
    var field = document.createElement('textarea');
    field.value = value;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.appendChild(field);
    field.select();
    try { document.execCommand('copy'); } catch (err) { /* nothing else to try */ }
    document.body.removeChild(field);
  }

  function copyLink() {
    var status = $('copy-status');
    var done = function () {
      status.textContent = 'Copied. Anyone with the link sees your score and can take the same test.';
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(shareLink).then(done, function () {
        fallbackCopy(shareLink);
        done();
      });
    } else {
      fallbackCopy(shareLink);
      done();
    }
  }

  function shareResult() {
    if (!currentResult) return;
    var text = S.shareMessage(state.test.name, currentResult);
    if (navigator.share) {
      navigator.share({ title: 'Life in the UK — ' + state.test.name, text: text, url: shareLink })
        .catch(function () { copyLink(); });
    } else {
      copyLink();
    }
  }

  /* ------------------------------------------------------------- listeners */

  $('btn-start').addEventListener('click', function () { startTest(TESTS[0]); });

  $('btn-browse').addEventListener('click', function (event) {
    event.preventDefault();
    $('test-grid').scrollIntoView({ block: 'start', behavior: 'smooth' });
  });

  $('btn-prev').addEventListener('click', function () { goTo(state.index - 1); });
  $('btn-next').addEventListener('click', function () {
    if (state.index === state.test.questions.length - 1) {
      var navigator = document.querySelector('.navigator');
      if (navigator) navigator.scrollIntoView({ block: 'center' });
      $('btn-submit').focus({ preventScroll: true });
    } else {
      goTo(state.index + 1);
    }
  });

  $('btn-submit').addEventListener('click', function () {
    var button = $('btn-submit');
    var answered = Object.keys(state.answers).length;
    var unanswered = state.test.questions.length - answered;

    if (unanswered > 0 && !button.dataset.confirm) {
      button.dataset.confirm = '1';
      button.textContent = 'Submit with ' + unanswered + ' unanswered';
      var warn = $('submit-warn');
      warn.textContent = unanswered + ' question' + (unanswered === 1 ? '' : 's') + ' left blank — they will count as incorrect.';
      warn.hidden = false;
      return;
    }
    finish(false);
  });

  $('btn-home').addEventListener('click', function () { leaveQuiz('tests'); });
  $('nav-study').addEventListener('click', function () { leaveQuiz('study'); });
  $('nav-tests').addEventListener('click', function () { leaveQuiz('tests', true); });

  $('btn-study-start').addEventListener('click', function () {
    var first = document.querySelector('.study-card');
    if (!first) return;
    var panel = first.querySelector('.study-notes');
    if (panel.hidden) first.querySelector('.study-actions .btn-ghost').click();
    first.scrollIntoView({ block: 'start' });
  });

  ['btn-to-tests', 'btn-study-tests'].forEach(function (id) {
    var button = $(id);
    if (button) button.addEventListener('click', function () { openTests('All'); });
  });

  $('btn-share').addEventListener('click', shareResult);
  $('btn-copy').addEventListener('click', copyLink);
  $('btn-again').addEventListener('click', function () { startTest(state.test); });
  $('btn-all').addEventListener('click', function () {
    renderTests();
    show('home');
  });
  $('btn-retake').addEventListener('click', function () { startTest(state.test); });

  document.addEventListener('keydown', function (event) {
    if (!$('screen-quiz').classList.contains('is-active') || !state.test) return;
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;

    if (event.key === 'ArrowRight') { goTo(state.index + 1); }
    else if (event.key === 'ArrowLeft') { goTo(state.index - 1); }
    else if (/^[1-6]$/.test(event.key)) {
      var position = parseInt(event.key, 10) - 1;
      if (position < currentQuestion().o.length) choose(position);
    }
  });

  /* ------------------------------------------------------------------ boot */

  buildGroups();
  renderStudy();
  renderHeroStats();
  renderFilters();
  renderTests();
  renderShared();
  if (!TESTS.length) {
    $('catalogue-note').textContent = 'Test data failed to load.';
  }
})();
