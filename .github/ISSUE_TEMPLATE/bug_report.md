---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

**Describe the problem:**
A clear and concise description of what the problem is. 
If you were executing a scan did it run, did it complete, did it save the file etc. 

**If you restart the software and try to recreate the problem does it still cause an error:**
Sometimes if a previous error is ignored that can lead to a series of errors that are likely
not problems and would be a waste of time to try and solve, so try to see if the problem
is truly THE issue and not the result of an unknown state due to a previously ignored (and un reported) error.

**Paste error message if you received one:**
Paste the complete error message (either screenshot or console message) here.
if you could also paste the
error message between  2 sets of these 3 characters that are backward leaning single quotes (key beside the number 1) **```**

Example:
```
(pyStxm39) C:\controls>conda activate C:\controls\Anaconda3\envs\pyStxm39

(pyStxm39) C:\controls>C:\controls\Anaconda3\condabin\conda.bat install -p C:/controls/Anaconda3/envs/pyStxm39 PyQt5-stubs==5.15.6.0 -y --no-deps
Collecting package metadata (current_repodata.json): failed

CondaSSLError: OpenSSL appears to be unavailable on this machine. OpenSSL is required to
download and install packages.

Exception: HTTPSConnectionPool(host='repo.anaconda.com', port=443): Max retries exceeded with url: /pkgs/main/win-64/current_repodata.json (Caused by SSLError("Can't connect to HTTPS URL because the SSL module is not available."))
```

**Steps To Reproduce issue:**
Specific steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior:**
A clear and concise description of what you expected to happen.


**Screenshots:**
If applicable, add screenshots to help explain your problem.

**Additional context:**
Add any other context about the problem here.
