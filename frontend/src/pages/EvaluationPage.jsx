import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';

function EvaluationPage() {
  const { examId, username } = useParams();
  const navigate = useNavigate();
  const [paper, setPaper] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [marks, setMarks] = useState({});
  const [msg, setMsg] = useState({ text: '', type: '' });

  useEffect(() => {
    const fetchPaper = async () => {
      try {
        const res = await api.get(`/admin/exams/${examId}/evaluation/${username}`);
        setPaper(res.data);
        
        // Initialize marks state with existing awarded marks
        const initialMarks = {};
        res.data.forEach(q => {
          if (q.answer_id) {
            initialMarks[q.answer_id] = q.marks_awarded || 0;
          }
        });
        setMarks(initialMarks);
      } catch (err) {
        setError(err.response?.data?.message || 'Error fetching evaluation data');
      } finally {
        setLoading(false);
      }
    };
    fetchPaper();
  }, [examId, username]);

  const showMsg = (text, type = 'success') => {
    setMsg({ text, type });
    setTimeout(() => setMsg({ text: '', type: '' }), 3000);
  };

  const handleMarkChange = (answerId, value) => {
    setMarks({ ...marks, [answerId]: parseInt(value) || 0 });
  };

  const handleSubmit = async () => {
    try {
      await api.post(`/admin/exams/${examId}/evaluation/${username}`, marks);
      showMsg('Evaluation saved successfully!');
      setTimeout(() => navigate('/admin'), 1500);
    } catch (err) {
      showMsg(err.response?.data?.message || 'Error saving evaluation', 'error');
    }
  };

  if (loading) return <div className="card">Loading paper...</div>;
  if (error) return <div className="card error-msg">{error}</div>;

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <button className="btn-secondary" onClick={() => navigate('/admin')} style={{ width: 'auto', marginBottom: '1rem' }}>
        ← Back to Admin
      </button>

      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2>Evaluate Student: {username}</h2>
        <p>Review the answers below and assign marks.</p>
      </div>

      {msg.text && (
        <div className={msg.type === 'error' ? 'error-msg' : 'success-msg'}>
          {msg.text}
        </div>
      )}

      {paper.map((q, idx) => {
        let options = [];
        try { options = JSON.parse(q.options); } 
        catch { options = typeof q.options === 'string' ? q.options.split(',') : []; }
        
        const isShortAnswer = (!options || options.length === 0 || (options.length === 1 && !options[0]));

        return (
          <div key={q.id} className="card">
            <h4>Q{idx + 1}: {q.question_text}</h4>
            <div style={{ marginBottom: '1rem', color: '#666', fontSize: '0.9rem' }}>
              Type: {isShortAnswer ? 'Short Answer' : 'MCQ'} | Maximum Marks: {q.marks}
            </div>

            <div style={{ background: '#f9f9f9', padding: '1rem', borderRadius: '4px', marginBottom: '1rem' }}>
              <strong>Student's Answer:</strong>
              <p style={{ margin: '0.5rem 0', whiteSpace: 'pre-wrap' }}>
                {q.student_answer || <em>(No answer submitted)</em>}
              </p>
            </div>

            {!isShortAnswer && (
              <div style={{ marginBottom: '1rem' }}>
                <strong>Correct Answer:</strong> {q.correct_answer}
              </div>
            )}

            {q.answer_id ? (
              <div className="form-group" style={{ maxWidth: '200px' }}>
                <label>Marks Awarded</label>
                <input
                  type="number"
                  min="0"
                  max={q.marks}
                  value={marks[q.answer_id] ?? 0}
                  onChange={(e) => handleMarkChange(q.answer_id, e.target.value)}
                  style={{ fontWeight: 'bold' }}
                />
              </div>
            ) : (
                <div style={{ color: 'var(--error)' }}>
                  Student did not submit an answer for this question. Marks = 0.
                </div>
            )}
          </div>
        );
      })}

      <div className="card" style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
        <button onClick={handleSubmit} style={{ width: 'auto', padding: '1rem 3rem' }}>
          Save Final Evaluation
        </button>
      </div>
    </div>
  );
}

export default EvaluationPage;
