import os
import uuid

import flask
import redis
import pygments
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name


app = flask.Flask(__name__)
app.redis = redis.Redis()


@app.route("/", methods=["GET"])
def index():
    return flask.render_template('index.html')


@app.route("/", methods=["POST"])
def create_page():
    data = flask.request.form.get('data', None)
    if not data:
        flask.abort(400)

    try:
        timeout = int(flask.request.form.get('timeout', 60 * 60))
    except (ValueError, TypeError):
        return 'invalid "timeout" value', 400
    if timeout < 1:
        return 'timeout has to be greater than 0', 400

    while True:
        key = str(uuid.uuid4())
        if app.redis.set(key, data, nx=True, ex=timeout):
            break

    return flask.render_template('set_success.html', key=key)


@app.route("/<key>", methods=["GET"])
def fetch_page(key):
    data = app.redis.get(key)
    if data is None:
        flask.abort(404)

    lexer_name = flask.request.args.get('lang', None)
    if not lexer_name:
        return flask.Response(data, content_type='text/plain; charset=utf-8')

    try:
        lexer = get_lexer_by_name(lexer_name, stripall=True)
    except pygments.util.ClassNotFound:
        return 'language "{}" not supported'.format(lexer_name), 400

    with_lines = 'nonu' not in flask.request.args

    formatter = HtmlFormatter(linenos=with_lines, cssclass="source")
    html = highlight(data, lexer, formatter)
    stylename = 'css/pygments/{}.css'.format(
            flask.request.args.get('style', 'tango'))
    return flask.render_template('source_code.html', html=html,
                                 stylename=stylename)


@app.route("/<key>", methods=["PUT"])
def change_page(key):
    data = flask.request.form.get('data', None)
    if not data:
        flask.abort(400)
    if not app.redis.set(key, data, xx=True):
        flask.abort(404)
    return flask.render_template('set_success.html', key=key)



if __name__ == "__main__":
    app.run(debug=bool(os.getenv('DEBUG', False)))
