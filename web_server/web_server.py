# Python 3 server example
from http.server import BaseHTTPRequestHandler, HTTPServer
from uritools import uricompose, urijoin, urisplit, uriunsplit
# from urlparse import urlparse, parse_qs

from HardwareBaseClass import *
from subrack_hardware import *

import time
import json

hostName = "0.0.0.0"
serverPort = 8081

def mangle_dict(input_dict):
    output_dict = {}
    for key in input_dict:
        value = input_dict[key][0]    # keep only first element
        value_array = value.split(',')
        if len(value_array) == 1:     # scalar
            if value.isnumeric():
                output_dict[key] = float(value)
            else:
                output_dict[key] = value
        else:
            value_list = []
            for v in value_array:
                if v.isnumeric():
                    v = float(v)
                value_list = value_list + [v]
            output_dict[key] = value_list
    return output_dict


class MyServer(BaseHTTPRequestHandler):

    def do_GET(self):
        # query_components = parse_qs(urlparse(self.path).query)
        query = urisplit(self.path)
        query_components = mangle_dict(query.getquerydict())
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        if 'type' in query_components.keys():
            command_type = query_components['type']
        else:
            command_type = None
        if 'param' in query_components.keys():
            command = query_components['param']
        else:
            command = None
        if 'value' in query_components.keys():
            value = query_components['value']
        else:
            value = None
        

        if command_type == 'command':
            query_answer = hardware.execute_command(command, value)
        elif command_type == 'setattribute':
            query_answer = hardware.set_attribute(command, value)
        elif command_type == 'getattribute': 
            query_answer = hardware.get_attribute(command)
        elif command_type == None:
            query_answer = {
                    'status': 'ERROR',
                    'info' : 'Missing keyword: type',
                    'command': command,
                    'retvalue': ''
                    }
        else:
            query_answer = {
                    'status': 'ERROR',
                    'info' : 'Invalid type: ' + str(command_type),
                    'command': command,
                    'retvalue': ''
                    }

        response = json.dumps(query_answer)
        self.wfile.write(bytes(response, "utf-8"))
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>")

hardware = SubrackHardware()

if __name__ == "__main__":        

    hardware.initialize()

    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
