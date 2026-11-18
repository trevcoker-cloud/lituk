/* Score, share-link and formatting helpers for the Life in the UK practice tests. */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.LITUK = api;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var SECONDS = 45 * 60;
  var PASS_RATIO = 0.75;

  function sameSet(a, b) {
    if (!a || !b) return false;
    var x = a.slice().sort(function (m, n) { return m - n; });
    var y = b.slice().sort(function (m, n) { return m - n; });
    if (x.length !== y.length) return false;
    for (var i = 0; i < x.length; i++) {
      if (x[i] !== y[i]) return false;
    }
    return true;
  }

  function grade(questions, answers) {
    answers = answers || {};
    var results = [];
    var score = 0;
    var unanswered = 0;

    questions.forEach(function (question, index) {
      var chosen = (answers[index] || []).slice();
      var answered = chosen.length > 0;
      var correct = answered && sameSet(chosen, question.a);
      if (!answered) unanswered++;
      if (correct) score++;
      results.push({
        answered: answered,
        correct: correct,
        chosen: chosen,
        expected: question.a.slice()
      });
    });

    var total = questions.length;
    var passMark = Math.ceil(total * PASS_RATIO);

    return {
      score: score,
      total: total,
      percent: total ? Math.round((score / total) * 100) : 0,
      passed: score >= passMark,
      passMark: passMark,
      unanswered: unanswered,
      incorrect: total - score - unanswered,
      results: results
    };
  }

  function formatTime(totalSeconds) {
    var s = Math.max(0, Math.round(totalSeconds || 0));
    var m = Math.floor(s / 60);
    var r = s % 60;
    return m + ':' + (r < 10 ? '0' : '') + r;
  }

  function shareUrl(base, testId, result) {
    return base + '?t=' + encodeURIComponent(testId) +
      '&s=' + result.score +
      '&d=' + Math.max(0, Math.round(result.secondsUsed || 0));
  }

  function parseShared(search) {
    var params;
    try {
      params = new URLSearchParams(search || '');
    } catch (err) {
      return null;
    }
    if (!params.get('t') || !params.has('s')) return null;

    var score = parseInt(params.get('s'), 10);
    var seconds = parseInt(params.get('d') || '0', 10);
    var total = 24;

    if (!isFinite(score) || score < 0 || score > total) return null;

    return {
      testId: params.get('t'),
      score: score,
      total: total,
      percent: Math.round((score / total) * 100),
      passed: score >= Math.ceil(total * PASS_RATIO),
      passMark: Math.ceil(total * PASS_RATIO),
      secondsUsed: isFinite(seconds) && seconds >= 0 ? seconds : 0
    };
  }

  function shareMessage(testName, result) {
    return 'I scored ' + result.score + '/' + result.total + ' (' + result.percent + '%) on ' + testName +
      ' of the Life in the UK practice tests \u2014 ' +
      (result.passed ? 'PASS. Can you beat it?' : 'just short of the ' + result.passMark + ' needed. Can you beat it?');
  }

  return {
    SECONDS: SECONDS,
    PASS_RATIO: PASS_RATIO,
    grade: grade,
    sameSet: sameSet,
    formatTime: formatTime,
    shareUrl: shareUrl,
    parseShared: parseShared,
    shareMessage: shareMessage
  };
});
