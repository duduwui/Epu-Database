import requests
s = requests.Session()
s.post('http://127.0.0.1:5000/login', data={'email': 'admin@epu.edu.iq', 'password': 'admin_password'})
r = s.get('http://127.0.0.1:5000/admin/feedback/teacher/47')
print('MANSOUR Avg:', 'Avg:' in r.text)
with open('test_res.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
