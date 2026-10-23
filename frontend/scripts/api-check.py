#!/usr/bin/env python3
"""Exercise only contact API rejection paths and the honeypot; never send mail."""
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
import os
url=os.environ.get('CONTACT_TEST_URL','http://127.0.0.1:4322/api/contact.php')
cases=[('GET',None,405,'Nur POST'),('POST',{},422,'Pflichtfelder'),('POST',{'company_website':'bot'},200,'angekommen'),('POST',{'name':'x'*121,'email':'valid@example.org','message':'Test','privacy':'on'},422,'Name'),('POST',{'name':'Test','email':'invalid','message':'Test','privacy':'on'},422,'gültige'),('POST',{'name':'Test','email':'a\r\n@example.org','message':'Test','privacy':'on'},422,'gültige'),('POST',{'name':'Test','email':'valid@example.org','message':'x'*5001,'privacy':'on'},422,'Nachricht'),('POST',{'message':'x'*33000},413,'groß')]
for method,data,status,text in cases:
    request=Request(url,data=None if data is None else urlencode(data).encode(),method=method)
    try:response=urlopen(request)
    except HTTPError as error:response=error
    body=response.read().decode()
    assert response.status==status and text in body,(response.status,body)
    print(method,status,text,'OK')
print('8 API-Checks erfolgreich; keine E-Mail versendet.')
