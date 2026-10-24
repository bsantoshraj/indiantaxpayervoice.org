# Shared by the HTTP and HTTPS servers in survey.conf.
proxy_set_header Host              $http_host;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $forwarded_proto;

# The LimeSurvey admin is served only on its own Cloudflare Access hostname
# (survey.conf, port 8090). Refuse every admin route here, in both URL formats
# LimeSurvey accepts: path (/index.php/admin/...) and query (?r=admin/...).
if ($arg_r ~* "^/?(admin|rest|installer)") { return 404; }
location ~* ^/(index\.php/)?(admin|rest|installer)(/|$) { return 404; }

# Internal: ask the gate whether this request carries a valid pass.
location = /_gate_check {
    internal;
    proxy_pass http://$gate_host:8000/gate/check;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header Cookie $http_cookie;
}

location /gate/ {
    limit_req zone=gate burst=30 nodelay;
    limit_req_status 429;
    proxy_pass http://$gate_host:8000;
}

# Survey-taking pages (path URL format: /index.php/<surveyid>, /index.php/survey/...).
location ~ ^/index\.php/([0-9]+|survey/) {
    auth_request /_gate_check;
    error_page 401 = @to_gate;
    limit_req zone=survey_post burst=60 nodelay;
    limit_req_status 429;
    proxy_pass http://$limesurvey_host:8080;
}

location @to_gate {
    return 302 /gate/?next=$request_uri;
}

# Survey assets and everything else (the admin is refused above).
location / {
    proxy_pass http://$limesurvey_host:8080;
}
