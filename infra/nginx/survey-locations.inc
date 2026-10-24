# Shared by the HTTP and HTTPS servers in survey.conf.
proxy_set_header Host              $http_host;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $forwarded_proto;

# Internal: ask the gate whether this request carries a valid pass.
location = /_gate_check {
    internal;
    proxy_pass http://gate:8000/gate/check;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header Cookie $http_cookie;
}

location /gate/ {
    limit_req zone=gate burst=30 nodelay;
    limit_req_status 429;
    proxy_pass http://gate:8000;
}

# Survey-taking pages (path URL format: /index.php/<surveyid>, /index.php/survey/...).
location ~ ^/index\.php/([0-9]+|survey/) {
    auth_request /_gate_check;
    error_page 401 = @to_gate;
    limit_req zone=survey_post burst=60 nodelay;
    limit_req_status 429;
    proxy_pass http://limesurvey:8080;
}

location @to_gate {
    return 302 /gate/?next=$request_uri;
}

# Admin UI, assets and everything else. Restrict /admin by IP or VPN in production.
location / {
    proxy_pass http://limesurvey:8080;
}
