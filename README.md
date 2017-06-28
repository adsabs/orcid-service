# orcid-service

Web micro service for ORCID

[![Travis Status](https://travis-ci.org/adsabs/orcid-service.png?branch=master)](https://travis-ci.org/adsabs/orcid-service)
[![Coverage Status](https://coveralls.io/repos/adsabs/orcid-service/badge.svg?branch=master&service=github)](https://coveralls.io/github/adsabs/orcid-service?branch=master)

#Installation:

```bash
git clone https://github.com/adsabs/orcid-service
virtualenv python
pip install -r requirements.txt
vim orcid_service/config.py # edit edit...
python orcid_service/app.py &
```

#Configuration:

The service needs to know few details

  - ORCID_API_ENDPOINT: usually https://api.orcid.org/v1.2
  - ORCID_CLIENT_SECRET: must be given to you by Orcid, do not
   share this secret!
  - ORCID_CLIENT_ID: given to you from Orcid


To check existing routes:

```
curl "http://127.0.0.1:5000/resources" | python -mjson.tool
```

For testing purposes, the application can be started with Flask-CORS
activated (good for testing ajax requests; ie. directly from Bumblebee)

```python
python orcid_service/cors.py
```

