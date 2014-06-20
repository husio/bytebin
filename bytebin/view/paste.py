import collections
import json

import flask
import pygments
import pygments.formatters
import pygments.lexers

from bytebin.models import Paste


app = flask.Blueprint('bytebin.view.paste', __name__)


@app.route("/", methods=["GET"])
def paste_form():
    lexers = {lx[0]: lx[1][0] for lx in pygments.lexers.get_all_lexers()}
    lexers = collections.OrderedDict(sorted(lexers.items()))
    return flask.render_template('create_form.html', lexers=lexers)


@app.route("/help", methods=["GET"])
def help():
    return flask.render_template('help.html')


@app.route("/", methods=["POST"])
def paste_create():
    content = flask.request.form.get('content', None)
    if not content:
        flask.abort(400)

    try:
        timeout = int(flask.request.form.get('timeout', 60 * 60))
    except (ValueError, TypeError):
        return 'invalid "timeout" value', 400
    if timeout < 1:
        return 'timeout has to be greater than 0', 400

    # convert to minutes
    if timeout > 60 * 60 * 24 * 2:
        return 'timeout has to be smaller than 2 days', 400

    one_use = flask.request.form.get('one_use', 'off') == 'on'
    language = flask.request.form.get('lang', '')

    if language == 'json':
        content = format_json(content)

    paste = Paste(content=content, one_use=one_use, lang=language)
    paste.save(timeout)

    # context negotiation does not work well here
    user_agent = flask.request.headers.get('user-agent')
    if one_use or (user_agent and user_agent.startswith('curl')):
        url = 'http://{}/{}\n'.format(flask.request.host, paste.key)
        return flask.Response(url, content_type='text/plain; charset=utf-8')

    return flask.redirect(flask.url_for('.paste_show', key=paste.key))


@app.route("/<key>", methods=["GET"])
def paste_show(key):
    paste = Paste.find(key)
    if paste.one_use == 'True':
        paste.delete()
    lexer_name = flask.request.args.get('lang', paste.lang)
    if lexer_name in (None, '', 'raw'):
        return flask.Response(paste.content,
                              content_type='text/plain; charset=utf-8')

    try:
        lexer = pygments.lexers.get_lexer_by_name(lexer_name, stripall=True)
    except pygments.util.ClassNotFound:
        return 'language "{}" not supported'.format(lexer_name), 400

    with_lines = 'lineno' in flask.request.args

    formatter = pygments.formatters.HtmlFormatter(linenos=with_lines,
                                                cssclass="source")
    html = pygments.highlight(paste.content, lexer, formatter)
    stylename = 'css/pygments/{}.css'.format(
            flask.request.args.get('style', 'tango'))
    return flask.render_template('source_code.html', html=html,
                                 stylename=stylename)


@app.route("/<key>", methods=["DELETE"])
def paste_delete(key):
    paste = Paste.find(key)
    paste.delete()
    return "Successfully deleted", 204


def format_json(raw, indent=4, sort_keys=True):
    """If possible, format string according to JSON syntax"""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return raw
    return json.dumps(data, indent=indent, sort_keys=sort_keys)



if __name__ == "__main__":
    app.run()
