A simple mcq and short question based exam system.

pages: login, exam, admin

login page:
2 options student login, admin login

student login:
 take username, password, exam_id
 if correct then redirect to exam page
 if incorrect then show error message
 use jwt with expiry time of exam_id exam

admin login:
 take username and password
 if correct then redirect to admin page
 if incorrect then show error message
 use jwt with 24 hours expiring time

exam page:
 show questions one by one
 each question has its own solving time
 when a question is answered, show next question
 if user doesn't answer a question within the time limit, show next question
 after all questions are answered, show result page
 
admin:
  login with username and password
  add exam, question, options, correct_answer, solving_time
  set student password for exam
  (students have no way to register, they can choose arbitrary username)

backend should be built in a single python file with venv
frontend should be built with react. use very minimal styling. the frontend should be light weight and fast. use vite for building the frontend. Keep security and exam integrity seriously.
