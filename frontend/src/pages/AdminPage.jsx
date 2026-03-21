import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

function AdminPage() {
  const [exams, setExams] = useState([]);
  const [newExamTitle, setNewExamTitle] = useState('');
  const [selectedExamId, setSelectedExamId] = useState('');
  
  const [qText, setQText] = useState('');
  const [qOptions, setQOptions] = useState('');
  const [qCorrect, setQCorrect] = useState('');
  const [qTime, setQTime] = useState('60');
  const [qMarks, setQMarks] = useState('1');
  
  const [sUsername, setSUsername] = useState('');
  const [sPassword, setSPassword] = useState('');
  
  const [results, setResults] = useState([]);
  const [questions, setQuestions] = useState([]);
  
  const [msg, setMsg] = useState({ text: '', type: '' });
  const navigate = useNavigate();

  const fetchExams = async () => {
    try {
      const res = await api.get('/admin/exams');
      setExams(res.data);
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        navigate('/login');
      } else {
        showMsg('Error fetching exams', 'error');
      }
    }
  };

  useEffect(() => {
    fetchExams();
  }, [navigate]);

  useEffect(() => {
    if (selectedExamId) {
      fetchResults();
      fetchQuestions();
    } else {
      setResults([]);
      setQuestions([]);
    }
  }, [selectedExamId]);

  const showMsg = (text, type = 'success') => {
    setMsg({ text, type });
    setTimeout(() => setMsg({ text: '', type: '' }), 3000);
  };

  const handleCreateExam = async (e) => {
    e.preventDefault();
    try {
      await api.post('/admin/exams', { title: newExamTitle });
      showMsg('Exam created!');
      setNewExamTitle('');
      fetchExams();
    } catch (err) {
      showMsg(err.response?.data?.message || 'Error creating exam', 'error');
    }
  };

  const fetchQuestions = async () => {
    if (!selectedExamId) return;
    try {
      const res = await api.get(`/admin/exams/${selectedExamId}/questions`);
      setQuestions(res.data);
    } catch (err) {
      showMsg('Error fetching questions', 'error');
    }
  };

  const handleAddQuestion = async (e) => {
    e.preventDefault();
    if (!selectedExamId) return showMsg('Select an exam first', 'error');
    
    // Convert comma separated to array. Empty array if empty string -> triggers short answer logic backend.
    const optionsArray = qOptions.trim() ? qOptions.split(',').map(s => s.trim()).filter(s => s !== '') : [];
    
    try {
      await api.post(`/admin/exams/${selectedExamId}/questions`, {
        question_text: qText,
        options: JSON.stringify(optionsArray),
        correct_answer: qCorrect.trim(),
        solving_time: parseInt(qTime),
        marks: parseInt(qMarks) || 1
      });
      showMsg('Question added!');
      setQText('');
      setQOptions('');
      setQCorrect('');
      setQTime('60');
      setQMarks('1');
      fetchQuestions();
    } catch (err) {
      showMsg(err.response?.data?.message || 'Error adding question', 'error');
    }
  };

  const handleEditMarks = async (qId, currentMarks) => {
    const newMarks = prompt("Enter new marks for this question:", currentMarks);
    if (newMarks === null || newMarks === "") return;
    try {
      await api.put(`/admin/exams/${selectedExamId}/questions/${qId}`, { marks: parseInt(newMarks) });
      showMsg('Marks updated!');
      fetchQuestions();
    } catch (err) {
      showMsg('Error updating marks', 'error');
    }
  };
  
  const handleDeleteQuestion = async (qId) => {
    if(!confirm('Are you sure you want to delete this question?')) return;
    try {
      await api.delete(`/admin/exams/${selectedExamId}/questions/${qId}`);
      showMsg('Question deleted!');
      fetchQuestions();
    } catch(err) {
      showMsg('Error deleting question', 'error');
    }
  }

  const handleAddStudent = async (e) => {
    e.preventDefault();
    if (!selectedExamId) return showMsg('Select an exam first', 'error');
    try {
      const res = await api.post(`/admin/exams/${selectedExamId}/students`, {
        username: sUsername,
        password: sPassword
      });
      showMsg(res.data.message, res.data.message.includes('already') ? 'error' : 'success');
      setSUsername('');
      setSPassword('');
    } catch (err) {
      showMsg('Error adding student', 'error');
    }
  };
  
  const fetchResults = async () => {
      if (!selectedExamId) return;
      try {
          const res = await api.get(`/admin/exams/${selectedExamId}/results`);
          setResults(res.data);
      } catch (err) {
          showMsg('Error fetching results', 'error');
      }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    navigate('/login');
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>Admin Dashboard</h2>
        <button onClick={handleLogout} className="btn-secondary" style={{ width: 'auto' }}>Logout</button>
      </div>

      {msg.text && (
        <div className={msg.type === 'error' ? 'error-msg' : 'success-msg'}>
          {msg.text}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="card">
          <h3>Create New Exam</h3>
          <form onSubmit={handleCreateExam}>
            <div className="form-group">
              <label>Exam Title</label>
              <input 
                value={newExamTitle} 
                onChange={(e) => setNewExamTitle(e.target.value)} 
                required 
              />
            </div>
            <button type="submit">Create</button>
          </form>
        </div>

        <div className="card">
          <h3>Select Exam to Manage</h3>
          <div className="form-group">
            <label>Exams</label>
            <select value={selectedExamId} onChange={(e) => setSelectedExamId(e.target.value)}>
              <option value="">-- Select Exam --</option>
              {exams.map(ex => (
                <option key={ex.id} value={ex.id}>{ex.title} (ID: {ex.id})</option>
              ))}
            </select>
          </div>
          {selectedExamId && (
              <button className="btn-secondary" onClick={fetchResults} style={{marginTop: '1rem'}}>
                Refresh Stats
              </button>
          )}
        </div>
      </div>

      {selectedExamId && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="card">
              <h3>Add Question</h3>
              <form onSubmit={handleAddQuestion}>
                <div className="form-group">
                  <label>Question Text</label>
                  <input value={qText} onChange={(e) => setQText(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Options (comma separated, leave blank for short answer)</label>
                  <input 
                    value={qOptions} 
                    onChange={(e) => setQOptions(e.target.value)} 
                    placeholder="A, B, C, D (or leave empty)" 
                  />
                </div>
                <div className="form-group">
                  <label>Correct Answer (leave blank for short answer)</label>
                  <input value={qCorrect} onChange={(e) => setQCorrect(e.target.value)} />
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Time (Seconds)</label>
                    <input type="number" value={qTime} onChange={(e) => setQTime(e.target.value)} required />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Marks</label>
                    <input type="number" value={qMarks} onChange={(e) => setQMarks(e.target.value)} required />
                  </div>
                </div>
                <button type="submit">Add Question</button>
              </form>
            </div>

            <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                <div className="card">
                  <h3>Add Student to Exam</h3>
                  <form onSubmit={handleAddStudent}>
                    <div className="form-group">
                      <label>Student Username</label>
                      <input value={sUsername} onChange={(e) => setSUsername(e.target.value)} required />
                    </div>
                    <div className="form-group">
                      <label>Student Password</label>
                      <input type="password" value={sPassword} onChange={(e) => setSPassword(e.target.value)} required />
                    </div>
                    <button type="submit">Add Student</button>
                  </form>
                </div>
                
                {results.length > 0 && (
                    <div className="card">
                        <h3>Exam Results</h3>
                        <ul style={{paddingLeft: '1rem'}}>
                            {results.map((r, i) => (
                                <li key={i} style={{marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                    <span>
                                      <strong>{r.username}</strong> - 
                                      Score: {r.score} 
                                      {r.evaluation_pending ? ' (Eval Pending)' : (r.finished ? ' (Finished)' : ' (In Progress)')}
                                    </span>
                                    {r.finished && (
                                      <button 
                                        onClick={() => navigate(`/admin/evaluate/${selectedExamId}/${r.username}`)}
                                        style={{ width: 'auto', padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}
                                      >
                                        Evaluate
                                      </button>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
          </div>

          <div className="card" style={{ marginTop: '1rem' }}>
             <h3>Current Questions ({questions.length})</h3>
             {questions.length === 0 ? <p>No questions yet.</p> : (
               <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
                 <thead>
                   <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                     <th style={{ padding: '0.5rem' }}>ID</th>
                     <th style={{ padding: '0.5rem' }}>Text</th>
                     <th style={{ padding: '0.5rem' }}>Type</th>
                     <th style={{ padding: '0.5rem' }}>Marks</th>
                     <th style={{ padding: '0.5rem' }}>Actions</th>
                   </tr>
                 </thead>
                 <tbody>
                   {questions.map(q => {
                     let opts = [];
                     try { opts = JSON.parse(q.options); } catch { opts = q.options; }
                     const isShort = !opts || opts.length === 0;

                     return (
                       <tr key={q.id} style={{ borderBottom: '1px solid #ddd' }}>
                         <td style={{ padding: '0.5rem' }}>{q.id}</td>
                         <td style={{ padding: '0.5rem' }}>{q.question_text}</td>
                         <td style={{ padding: '0.5rem' }}>{isShort ? 'Short Answer' : 'MCQ'}</td>
                         <td style={{ padding: '0.5rem' }}>{q.marks}</td>
                         <td style={{ padding: '0.5rem' }}>
                           <button className="btn-secondary" onClick={() => handleEditMarks(q.id, q.marks)} style={{ width: 'auto', padding: '0.2rem 0.5rem', marginRight: '0.5rem', fontSize: '0.8rem' }}>Edit Mark</button>
                           <button style={{ backgroundColor: '#d9534f', width: 'auto', padding: '0.2rem 0.5rem', fontSize: '0.8rem' }} onClick={() => handleDeleteQuestion(q.id)}>Delete</button>
                         </td>
                       </tr>
                     );
                   })}
                 </tbody>
               </table>
             )}
          </div>
        </>
      )}
    </div>
  );
}

export default AdminPage;
