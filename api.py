#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

from api_requests import ClientsInterestsRequest, OnlineScoreRequest, MethodRequest
from scoring import get_score, get_interests
from constants import SALT, ADMIN_SALT, OK, BAD_REQUEST, FORBIDDEN, \
    NOT_FOUND, INVALID_REQUEST, INTERNAL_ERROR, ERRORS


def check_auth(request):
    logging.info(f'Trying authorization as "{request.login}"')
    if request.is_admin:
        digest = hashlib.sha512(
            (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode(
                'utf-8')).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode(
            'utf-8')).hexdigest()
    if digest == request.token:
        logging.info(f'Authorization success')
        return True
    logging.info(
        f'Authorization failed, expected "{digest}",'
        f'\n but "{request.token}" received')
    return False


def authorization(func):
    def wrapper(request, ctx, store):
        response, code = ERRORS.get(FORBIDDEN), FORBIDDEN
        if check_auth(request):
            response, code = func(request, ctx, store)
        return response, code

    return wrapper


def method_handler(request, ctx, store):
    try:
        req = MethodRequest(request.get('body'))
        logging.info(f'Requested method value: "{req.method}"')
        if req.method == 'online_score':
            response, code = online_score_handler(req, ctx, store)
        elif req.method == 'clients_interests':
            response, code = clients_interests_handler(req, ctx, store)
        else:
            logging.info(f'Unavailable method value')
            response, code = ERRORS.get(INVALID_REQUEST), INVALID_REQUEST
        return response, code
    except (ValueError, AttributeError):
        return ERRORS.get(INVALID_REQUEST), INVALID_REQUEST


@authorization
def online_score_handler(req, ctx, store):
    arguments = req.arguments
    online_score = OnlineScoreRequest(arguments)
    ctx['has'] = [key for key, val in arguments.items() if val is not None]
    if req.is_admin:
        score = int(ADMIN_SALT)
    else:
        score = get_score(store, online_score.phone, online_score.email,
                          online_score.birthday,
                          online_score.gender, online_score.first_name,
                          online_score.last_name)
    response = {'score': score}
    logging.info(f'Score: {score}')
    return response, OK


@authorization
def clients_interests_handler(req, ctx, store):
    clients_interests = ClientsInterestsRequest(req.arguments)
    ctx['nclients'] = len(clients_interests.client_ids)
    interests = {_id: get_interests(store, _id) for _id in
                 clients_interests.client_ids}
    logging.info(f'Client interest: {interests}')
    return interests, OK


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    @staticmethod
    def get_request_id(headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        logging.info(f'New request context: {context}')
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
            logging.info(f'Received request: {request}')
        except Exception as e:
            code = BAD_REQUEST
            logging.info(e)

        if request:
            path = self.path.strip("/")
            if path in self.router:
                logging.info(f'Requested path: {path}')
                try:
                    response, code = self.router[path](
                        {"body": request, "headers": self.headers}, context,
                        self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                logging.info(f'{path} is not valid path')
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"),
                 "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode('utf-8'))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
