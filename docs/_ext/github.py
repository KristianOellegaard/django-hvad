# Sphinx helper for github issue references
from docutils import nodes
from docutils.parsers.rst.roles import set_classes

ISSUE_URL = 'https://github.com/{owner}/{repo}/issues/{num}'

def github_issue_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    try:
        issuenum = int(text)
        if issuenum <= 0:
            raise ValueError()
    except ValueError:
        msg = inliner.reporter.error(
            'Issuse number must be a strictly positive integer. Number "%s" '
            'is invalid.' % text, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    ref = ISSUE_URL.format(
        owner = inliner.document.settings.env.config['github_owner'],
        repo = inliner.document.settings.env.config['github_repo'],
        num = issuenum,
    )
    set_classes(options)
    node = nodes.reference(rawtext, '#%d' % issuenum, refuri=ref, **options)
    return [node], []

def setup(app):
    app.add_config_value('github_owner', None, 'html')
    app.add_config_value('github_repo', None, 'html')
    app.add_role('issue', github_issue_role)
