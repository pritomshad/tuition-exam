import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

function ExamPage() {
  const [question, setQuestion]         = useState(null);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState('');
  const [selectedOption, setSelectedOption] = useState('');
  const [timeRemaining, setTimeRemaining]   = useState(0);

  // Review-mode state (shown after submit / timeout)
  const [review, setReview]             = useState(null); // { studentAnswer, correctAnswer, isCorrect, finished }
  const [nextLoading, setNextLoading]   = useState(false);

  const navigate = useNavigate();
  const intervalRef = useRef(null);

  /* ── helpers ─────────────────────────────────────────── */

  const clearTimer = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  /* ── fetch next question ─────────────────────────────── */

  const fetchQuestion = async () => {
    try {
      setLoading(true);
      setReview(null);
      setSelectedOption('');
      setError('');
      const res = await api.get('/student/question');
      if (res.data.finished) {
        navigate('/result');
        return;
      }
      setQuestion(res.data);
      setTimeRemaining(res.data.time_remaining);
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        navigate('/login');
      } else {
        setError(err.response?.data?.message || 'Error fetching question');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestion();
    return () => clearTimer();
  }, []);

  /* ── countdown timer (only while question is active) ── */

  useEffect(() => {
    // Don't run timer during review or when there's no question
    if (review || !question || timeRemaining <= 0) return;

    clearTimer();
    intervalRef.current = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearTimer();
          // Use a ref callback so we always have the latest selectedOption
          setSelectedOption((cur) => {
            submitAnswer(cur, true /* timeUp */);
            return cur;
          });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearTimer();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question, review]);

  /* ── submit answer ───────────────────────────────────── */

  const submitAnswer = async (answer, timeUp = false) => {
    clearTimer();
    try {
      const res = await api.post('/student/answer', { answer });
      // Show review panel regardless of whether exam is finished
      setReview({
        studentAnswer: timeUp && !answer ? '(no answer — time expired)' : answer || '(no answer)',
        correctAnswer: res.data.correct_answer,
        isCorrect:     res.data.is_correct,
        finished:      res.data.finished,
      });
    } catch (err) {
      setError(err.response?.data?.message || 'Error submitting answer');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    submitAnswer(selectedOption);
  };

  /* ── "Next Question" button ──────────────────────────── */

  const handleNext = async () => {
    if (review?.finished) {
      navigate('/result');
      return;
    }
    setNextLoading(true);
    await fetchQuestion();
    setNextLoading(false);
  };

  /* ── early returns ───────────────────────────────────── */

  if (loading)  return <div className="card">Loading next question...</div>;
  if (error)    return <div className="card error-msg">{error}</div>;
  if (!question) return null;

  let options = [];
  try {
    options = JSON.parse(question.options);
  } catch {
    options = typeof question.options === 'string' ? question.options.split(',') : [];
  }
  const isShortAnswer = !options || options.length === 0 || (options.length === 1 && !options[0]);

  /* ── render ─────────────────────────────────────────── */

  return (
    <div className="card">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <span style={{ fontSize: '1.2rem', color: 'var(--primary)', fontWeight: 'bold' }}>
          Question {question.current_index + 1} of {question.total_questions}
        </span>
        {!review && (
          <div className={`timer ${timeRemaining < 10 ? 'warning' : ''}`}>
            ⏰ {formatTime(timeRemaining)}
          </div>
        )}
      </div>

      {/* Question text */}
      <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>{question.question_text}</h3>
      <div style={{ marginBottom: '2rem', color: '#666' }}>Marks: {question.marks}</div>

      {/* ── REVIEW PANEL ── */}
      {review ? (
        <div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '1.5rem',
            marginBottom: '2rem',
          }}>
            {/* Student's answer */}
            <div style={{
              padding: '1.25rem',
              borderRadius: '10px',
              border: `2px solid ${review.isCorrect ? 'var(--success, #22c55e)' : 'var(--danger, #ef4444)'}`,
              background: review.isCorrect ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)',
            }}>
              <div style={{ fontWeight: 700, marginBottom: '0.5rem', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#555' }}>
                Your Answer
              </div>
              <div style={{ fontSize: '1.05rem' }}>
                {review.isCorrect ? '✅' : '❌'} {review.studentAnswer}
              </div>
            </div>

            {/* Correct answer */}
            <div style={{
              padding: '1.25rem',
              borderRadius: '10px',
              border: '2px solid var(--success, #22c55e)',
              background: 'rgba(34,197,94,0.06)',
            }}>
              <div style={{ fontWeight: 700, marginBottom: '0.5rem', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#555' }}>
                Correct Answer
              </div>
              <div style={{ fontSize: '1.05rem' }}>
                ✅ {review.correctAnswer}
              </div>
            </div>
          </div>

          <button
            onClick={handleNext}
            disabled={nextLoading}
            style={{ width: '100%' }}
          >
            {nextLoading
              ? 'Loading…'
              : review.finished
              ? 'See Results'
              : 'Next Question →'}
          </button>
        </div>
      ) : (
      /* ── QUESTION FORM ── */
        <form onSubmit={handleSubmit}>
          <div className="options-list" style={{ marginBottom: '2rem' }}>
            {isShortAnswer ? (
              <textarea
                rows="5"
                style={{ width: '100%', padding: '1rem', border: '1px solid var(--border)', borderRadius: '4px' }}
                placeholder="Type your answer here..."
                value={selectedOption}
                onChange={(e) => setSelectedOption(e.target.value)}
              />
            ) : (
              options.map((opt, idx) => (
                <label key={idx} className="option-item">
                  <input
                    type="radio"
                    name="option"
                    value={opt.trim()}
                    checked={selectedOption === opt.trim()}
                    onChange={(e) => setSelectedOption(e.target.value)}
                  />
                  {opt.trim()}
                </label>
              ))
            )}
          </div>
          <button type="submit" disabled={!isShortAnswer && !selectedOption}>
            Submit Answer
          </button>
        </form>
      )}
    </div>
  );
}

export default ExamPage;
