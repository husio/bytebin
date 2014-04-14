import difflib
import os

import flask
from redis import Redis
import pygments
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from models import Paste


app = flask.Flask(__name__)
app.debug = bool(os.getenv('DEBUG', False))
redis = Redis(db=int(os.getenv('REDIS_DATABSE', 3)))
Paste.set_connection(redis)


@app.route("/", methods=["GET"])
def paste_form():
    return flask.render_template('create_form.html')


@app.route("/help", methods=["GET"])
def help():
    return flask.render_template('help.html')


@app.route("/", methods=["POST"])
def pate_create():
    content = flask.request.form.get('content', None)
    if not content:
        flask.abort(400)

    try:
        timeout = int(flask.request.form.get('timeout', 60))
    except (ValueError, TypeError):
        return 'invalid "timeout" value', 400
    if timeout < 1:
        return 'timeout has to be greater than 0', 400

    # convert to minutes
    if timeout > 60 * 60 * 24 * 2:
        return 'timeout has to be smaller than 2 days', 400

    paste = Paste(content=content)
    paste.save(timeout)

    app.logger.info('page created by %s, size %s', flask.request.remote_addr,
                    len(paste.content))

    # context negotiation does not work well here
    user_agent = flask.request.headers.get('user-agent')
    if user_agent and user_agent.startswith('curl'):
        url = 'http://{}/{}\n'.format(flask.request.host, paste.key)
        return flask.Response(url, content_type='text/plain; charset=utf-8')

    return flask.redirect(flask.url_for('.paste_show', key=paste.key))


@app.route("/<key_1>/diff/<key_2>", methods=["GET"])
def paste_diff(key_1, key_2):
    keys = [key_1, key_2]
    values = app.redis.mget([key_1, key_2])
    for key, value in zip(keys, values):
        if not value:
            return "Value is missing: {}".format(key), 404
    values = [v.decode('utf8').split('\n') for v in values]
    diff = difflib.unified_diff(*values)
    content = "\n".join(diff)
    if False:
        return flask.Response(content, content_type='text/plain; charset=utf-8')

    lexer = get_lexer_by_name('diff', stripall=True)
    formatter = HtmlFormatter(linenos=False, cssclass="source")
    html = highlight(content, lexer, formatter)
    stylename = 'css/pygments/{}.css'.format(
            flask.request.args.get('style', 'tango'))
    return flask.render_template('source_code.html', html=html,
                                 stylename=stylename)


@app.route("/<key>", methods=["GET"])
def paste_show(key):
    try:
        paste = Paste.find(key)
    except Paste.NotFound:
        flask.abort(404)

    lexer_name = flask.request.args.get('lang', None)
    if not lexer_name:
        return flask.Response(paste.content,
                              content_type='text/plain; charset=utf-8')

    try:
        lexer = get_lexer_by_name(lexer_name, stripall=True)
    except pygments.util.ClassNotFound:
        return 'language "{}" not supported'.format(lexer_name), 400

    with_lines = 'lineno' in flask.request.args

    formatter = HtmlFormatter(linenos=with_lines, cssclass="source")
    html = highlight(paste.content, lexer, formatter)
    stylename = 'css/pygments/{}.css'.format(
            flask.request.args.get('style', 'tango'))
    return flask.render_template('source_code.html', html=html,
                                 stylename=stylename)


@app.route("/<key>", methods=["DELETE"])
def paste_delete(key):
    try:
        paste = Paste.find(key)
        paste.delete()
    except Paste.NotFound:
        flask.abort(404)
    return "Successfully deleted", 204


@app.errorhandler(404)
def page_not_found(e):
    return "Page not found", 404


if __name__ == "__main__":
    app.run()
