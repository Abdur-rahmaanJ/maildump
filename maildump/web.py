import json
from cStringIO import StringIO
from datetime import datetime
from flask import Flask, render_template, jsonify, request, url_for, send_file
from logbook import Logger
from functools import wraps

import maildump
import maildump.db as db


app = Flask(__name__)
app._logger = log = Logger(__name__)


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(repr(obj) + ' is not JSON serializable')


def jsonify(*args, **kwargs):
    return app.response_class(json.dumps(dict(*args, **kwargs), default=_json_default, indent=4),
                              mimetype='application/json')


def bool_arg(arg):
    return arg in ('yes', 'true', '1')


def rest(f):
    """Decorator for simple REST endpoints.

    Functions must return one of these values:
    - a dict to jsonify
    - nothing for an empty 204 response
    - a tuple containing a status code and a dict to jsonify
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        ret = f(*args, **kwargs)
        if ret is None:
            response = jsonify()
            response.status_code = 204  # no content
        elif isinstance(ret, app.response_class):
            response = ret
        elif isinstance(ret, tuple):
            # code, result_dict|msg_string
            if isinstance(ret[1], basestring):
                response = jsonify(msg=ret[1])
            else:
                response = jsonify(**ret[1])
            response.status_code = ret[0]
        else:
            response = jsonify(**ret)
        return response
    return wrapper


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/', methods=('DELETE',))
@rest
def terminate():
    log.debug('Terminate request received')
    maildump.stop()


@app.route('/messages', methods=('DELETE',))
@rest
def delete_messages():
    db.delete_messages()


@app.route('/messages', methods=('GET',))
@rest
def get_messages():
    # TODO: SSE/WebSocket support
    lightweight = not bool_arg(request.args.get('full'))
    return {
        'messages': db.get_messages(lightweight)
    }


def _part_url(part):
    return url_for('get_message_part', message_id=part['message_id'], cid=part['cid'])


@app.route('/messages/<int:message_id>.json', methods=('GET',))
@rest
def get_message_info(message_id):
    lightweight = not bool_arg(request.args.get('full'))
    message = db.get_message(message_id, lightweight)
    if not message:
        return 404, 'message does not exist'
    message['formats'] = ['source']
    if db.message_has_plain(message_id):
        message['formats'].append('plain')
    if db.message_has_html(message_id):
        message['formats'].append('html')
    message['attachments'] = [dict(part, href=_part_url(part)) for part in db.get_message_attachments(message_id)]
    return message


@app.route('/messages/<int:message_id>/parts/<int:cid>', methods=('GET',))
@rest
def get_message_part(message_id, cid):
    part = db.get_message_part_cid(message_id, cid)
    if not part:
        return 404, 'part does not exist'
    io = StringIO(part['body'])
    io.seek(0)
    response = send_file(io, part['type'], part['is_attachment'], part['filename'])
    response.charset = part['charset'] or 'utf-8'
    return response