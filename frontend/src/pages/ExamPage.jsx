import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

function ExamPage() {
  const [question, setQuestion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedOption, setSelectedOption] = useState('');
  const [timeRemaining, setTimeRemaining] = useState(0);
  const navigate = useNavigate();

  const fetchQuestion = async () => {
    try {
      setLoading(true);
      const res = await api.get('/student/question');
      if (res.data.finished) {
        navigate('/result');
        return;
      }
      setQuestion(res.data);
      setTimeRemaining(res.data.time_remaining);
      setSelectedOption('');
      setError('');
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
  }, []);

  useEffect(() => {
    if (timeRemaining <= 0 || !question) return;

    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          submitAnswer(selectedOption || ''); // Auto-submit when time is up
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [timeRemaining, question, selectedOption]);

  const submitAnswer = async (answer) => {
    try {
      const res = await api.post('/student/answer', { answer });
      if (res.data.finished) {
        navigate('/result');
      } else {
        fetchQuestion();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Error submitting answer');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    submitAnswer(selectedOption);
  };

  if (loading) return <div className="card">Loading next question...</div>;
  if (error) return <div className="card error-msg">{error}</div>;
  if (!question) return null;

  let options = [];
  try {
    options = JSON.parse(question.options);
  } catch (e) {
    options = typeof question.options === 'string' ? question.options.split(',') : [];
  }

  const isShortAnswer = (!options || options.length === 0 || (options.length === 1 && !options[0]));

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <span style={{ fontSize: '1.2rem', color: 'var(--primary)', fontWeight: 'bold' }}>
          Question {question.current_index + 1} of {question.total_questions}
        </span>
        <div className={`timer ${timeRemaining < 10 ? 'warning' : ''}`}>
          ⏰ {formatTime(timeRemaining)}
        </div>
      </div>

      <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>{question.question_text}</h3>
      <div style={{ marginBottom: '2rem', color: '#666' }}>
          Marks: {question.marks}
      </div>

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
        <button type="submit" disabled={!isShortAnswer && !selectedOption}>Submit Answer</button>
      </form>
    </div>
  );
}

export default ExamPage;
