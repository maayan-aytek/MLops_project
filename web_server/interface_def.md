# Interface between client and the PictureServer

| Version | Date       | Author | Description   |
|---------|------------|--------|---------------|
| v0.0    | 2024-03-17 | Noam Cohen | Initial draft |
| v0.1    | 2024-06-06 | Noam Cohen | minor protocol changes|
| v0.11   | 2024-06-23 | Noam Cohen | replace 'pending' ->'running' |
| v0.12   | 2024-07-02 | Noam Cohen | add error response |
| v0.2    | 2024-07-02 | Noam Cohen | update login/logout requirements |

<hr>

**NOTE:** This Markdown file is best viewed with VisualStudio code (press CTRL shift v)

This document defines the wire protocol between an http client and the server in the project.

The words 'MUST', 'SHALL', 'SHOULD' are as defined in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)

The set of commands supported by the server may increase over time.

All commands SHALL be sent using https scheme.

see [REST API](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)<br>
see [Idempotent commands](https://restfulapi.net/idempotent-rest-apis/)

## Command format

When sending file (the image file for example), use FormData. Otherwise, use json


### Server response
The response SHALL have Content-Type=application/json

Response of the server SHALL have a json body. If the response is error, the body SHALL be:
```asciidoc
{'error': {'code': number, 'message': 'image is wrong format'}
}
```
If the response is success, the body SHALL be [with a few documented exceptions]
```
{ /* defined in each command */}
```

### Response codes
The response codes SHALL be standard HTTP status codes. <br>
Each command specifies the possible status codes.

# Command list 

## Upload image file to inference engine


Endpoint: POST /upload_image  formdata<br>
requires authentication: YES

Content-Disposition: form-data; name="image"; filename="somepic.png"
Content-Type: image/png

Supported image types SHALL be at least PNG and JPEG. *If a file is not recognized, the server SHALL return code 400*

The server MAY respond synchronously, giving the result with code 200, or async, returning 202 and a request-id.

The server SHOULD be consistent working sync/async. Either all uploads are async or all are sync.


Response: 200, 202, 400, 401

if 202: {'request_id': i32 } <br>
if 200: { 'matches': [ {'name': string, 'score': number}]}

*example* 
```
{'matches': [{'name': 'tomato', 'score': 0.9}, {'name':'carrot', 'score': 0.02}]}
```

# Get result from server
Endpoint: GET /result/\<request-id\> <br>
requires authentication: YES

Response: 200, 401, 404

if 404: ID not found<br>
if 401: not authenticated <br>
if 200: 
```
{ 'status': 'completed' | 'running' | 'error',

if operation succeeded:
'matches': [ {'name': string, 'score': number}...]
if operation errored:
'error': {'code': number, 'message': string}
}
```

This endpoint does not change the server state. 
status is **running** if the job runs now, or is still enqueued. 

*NOTE:* The server return 200 even when the job failed since the *GET /result/* succeeds

*SECURITY NOTE*: Any authenticated user can call this endpoint. It is possibe that USER A will upload an image, and USER B will get the result. Therefore, the request-id SHOULD be kept secret.




## Get server status
Endpoint: GET /status <br>
requires authentication: NO

Response: 200
```
{'status':
   'uptime': number /* seconds */,
   'processed:{
        'success': number,
        'fail': number,
        'running': number,
        'queued': number
   },
  'health': 'ok' |'error',
  'api_version': number
}
```
**uptime** is the numbers of seconds since the server started.

**success** is the number of jobs completed successfully<br>
**fail** is the number of jobs completed with some error <br>
**running** is the number of jobs currently running<br>
**queued** is the number of jobs waiting to run. Use 0 (zero) if a queue is not implemented.





## Login
Authentication is done using "basic authentication" <br>
requires authentication: NO

POST /login 

```
formdata:
  username: string
  password: string
```
reponse: 200, 401

**Informative NOTE**: In this simple server, the username and password are hardcoded. There is no way to change it.

Response body MAY be "{}". It MAY be a redirect to the "/" endpoint

## Logout
requires authentication: YES

Log out the current user. The user MUST login again in order to use "upload_image".

Response body SHALL be "{}"
Informative note: this means that redirect is not allowed.


GET /logout

response: 200 : logout succesful
          401 : was not logged in


