#!/usr/bin/python3
# Python 3 server example
from http.server import BaseHTTPRequestHandler, HTTPServer
from uritools import uricompose, urijoin, urisplit, uriunsplit
# from urlparse import urlparse, parse_qs
import logging

from HardwareBaseClass import *
from subrack_hardware import *

import time
import json

hostName = "0.0.0.0"
serverPort = 8081

def mangle_dict(input_dict):
    """
    Takes a query dictionary from the http.getquerydict()
    FOr each element keeps only the first element (list of values)
    Converts it to scalar if it is a list of 1 element
    If some values are numeric convert them to numbers
    """
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
    """
    Request handler, subclassed from http package
    """

    def do_GET(self):
        """
        Callback for GET request
        Retrieves query, and splits it into a dictionary
        Use mangle_dict to convert 1-lists to scalars, 
        and numeric strings to numbers
        Calls appropriate methods of the hardware class. 
        Formats the return dictionary to json and send it as response
        """
        # query_components = parse_qs(urlparse(self.path).query)
        query = urisplit(self.path)
        query_components = mangle_dict(query.getquerydict())
        logger.debug('Receved: '+str(query_components))
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
        logger.debug('Sent: '+response)

hardware = SubrackHardware()
logging.basicConfig(level=logging.ERROR)
logger=logging.getLogger('webServer')

if __name__ == "__main__":        

    hardware.initialize()
    webServer = HTTPServer((hostName, serverPort), MyServer)
    logger.info("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
