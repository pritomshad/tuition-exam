import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

function ResultPage() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const res = await api.get('/student/result');
        setResult(res.data);
      } catch (err) {
        if (err.response?.status === 401 || err.response?.status === 403) {
          navigate('/login');
        } else {
          setError(err.response?.data?.message || 'Error fetching result');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    navigate('/login');
  };

  if (loading) return <div className="card">Loading results...</div>;

  return (
    <div style={{ maxWidth: '800px', margin: '2rem auto' }}>
      <div className="card" style={{ textAlign: 'center' }}>
        <h2>Exam Completed</h2>
        
        {error ? (
          <div className="error-msg">{error}</div>
        ) : result?.evaluation_pending ? (
          <div style={{ margin: '2rem 0', padding: '2rem', background: '#fff3cd', color: '#856404', borderRadius: '4px' }}>
            <h3 style={{ margin: 0 }}>Evaluation Pending ⏳</h3>
            <p style={{ marginTop: '1rem' }}>Your teacher is reviewing your short answers. Check back later for your final score!</p>
          </div>
        ) : result ? (
          <div style={{ margin: '2rem 0' }}>
            <div style={{ fontSize: '4rem', color: 'var(--primary)', fontWeight: 'bold' }}>
              {result.score} / {result.total}
            </div>
            <p style={{ fontSize: '1.2rem', marginTop: '1rem', color: '#666' }}>
              Your final score
            </p>
          </div>
        ) : null}

        <button onClick={handleLogout} style={{ marginTop: '2rem', width: 'auto', padding: '0.75rem 3rem' }}>
          Logout
        </button>
      </div>

      {result && !result.evaluation_pending && result.paper && result.paper.length > 0 && (
         <div style={{ marginTop: '2rem' }}>
            <h3>Evaluated Paper</h3>
            {result.paper.map((q, idx) => (
                <div key={q.id} className="card" style={{ marginBottom: '1rem' }}>
                   <h4>Q{idx + 1}: {q.question_text}</h4>
                   <div style={{ color: '#666', fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                      Marks Awarded: <strong>{q.marks_awarded} / {q.marks}</strong>
                   </div>
                   
                   <div style={{ background: '#f9f9f9', padding: '1rem', borderRadius: '4px', marginBottom: '0.5rem' }}>
                      <strong>Your Answer:</strong>
                      <p style={{ margin: '0.5rem 0', whiteSpace: 'pre-wrap' }}>
                        {q.student_answer || <em>(No answer submitted)</em>}
                      </p>
                   </div>
                   
                   {q.options && q.options !== '[]' && q.options.trim() !== '' && (
                      <div style={{ background: '#e8f5e9', color: '#2e7d32', padding: '0.5rem', borderRadius: '4px' }}>
                          <strong>Correct MCQ Answer:</strong> {q.correct_answer}
                      </div>
                   )}
                </div>
            ))}
         </div>
      )}
    </div>
  );
}

export default ResultPage;
