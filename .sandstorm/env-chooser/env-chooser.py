#!/usr/bin/python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import json, os, tempfile, sys

os.chdir(os.path.split(__file__)[0])
page_template = open("page.html").read()
form_template = open("form.html").read()
field_template = open("field.html").read()
option_template = open("option.html").read()
env_var_options = json.load(open("env_var_options.json"))

# TODO css

[_, serverPort, envOutputPath] = sys.argv
serverPort = int(serverPort)

hostName = "0.0.0.0"

class MyServer(BaseHTTPRequestHandler):
    @staticmethod
    def make_page():
        return page_template.format(
            form=form_template.format(
                fields="\n".join(
                    field_template.format(
                        options="\n".join(
                            option_template.format(**option)
                            for option in field['options']
                        ),
                        **{key: val for (key, val) in field.items() if key != "options"}
                    )
                    for field in env_var_options
                )
            )
        )

    def get_vars_in(self):
        parsed_url = urlparse(self.path)
        vars_in = parse_qs(parsed_url.query)
        vars_in_cleaned = {}
        for key, val in vars_in.items():
            # Assume we're not passing in arrays for this
            [val] = val
            vars_in_cleaned[key] = val
        return vars_in_cleaned

    def validate(self, vars_in):
        for var in env_var_options:
            if var['env_var'] not in vars_in:
                return False
            valid_values = {opt["value"] for opt in var['options']}
            if vars_in[var['env_var']] not in valid_values:
                return False
        return True

    def write_env(self, new_env):
        tmp = tempfile.NamedTemporaryFile(dir=os.path.split(envOutputPath)[0])
        with open(tmp.name, 'w') as f:
            f.write(
                '\n'.join(
                    'export ' + key + '=' + var
                    for (key, var) in new_env.items()
                )
            )
        os.rename(tmp.name, envOutputPath)

    def do_GET(self):
        vars_in = self.get_vars_in()
        if self.validate(vars_in):
            self.write_env(vars_in)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # can make this marginally faster and more reliable by returning
            # 503 and using Caddy's load balancer to wait for the service to start
            self.wfile.write(bytes("<script>setTimeout(() => window.location = '/', 100)</script>", "utf-8"))
            # Quit so that the service can start with the new env vars
            exit(0)

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(bytes(self.make_page(), "utf-8"))

if __name__ == "__main__":
    if os.path.exists(envOutputPath): # TODO - valiadte it tho. sucks.
        exit(0)

    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
