from os import listdir
from os.path import isfile, join
import json

import pytest


def load_files(category):
    path = "tests/test-data/%s/" % category
    onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
    results = []
    for file in onlyfiles:
        with open(join(path, file), "r") as f:
            results += json.load(f)['results']
    return results


@pytest.fixture
def load_results():
    results = load_files('objects')
    yield results


@pytest.fixture
def load_comments():
    results = load_files('comments')
    yield results


def test_contentwrapper(load_results, caplog, monkeypatch):
    # make sure that no requests are made, ever
    import requests

    def mock_request(*args, **kwargs):
        raise RuntimeError("Unable to make requests in test mode")
    monkeypatch.setattr(requests.Session,
                        "request",
                        mock_request)

    from congruence.args import load_config
    load_config(args=['--config', './config.yaml.sample'])

    from congruence.confluence import PageView, SingleCommentView
    from congruence.objects import ContentWrapper, Generic
    from congruence.views.listbox import ColumnListBoxEntry
    import congruence.confluence
    from congruence.app import app
    app.main(dummy=True)

    def mock_get_comments(*args, **kwargs):
        return {}
    monkeypatch.setattr(congruence.confluence,
                        "get_comments_of_page",
                        mock_get_comments)

    results = load_results
    for r in results:
        obj = ContentWrapper(r)
        assert r['title'] == obj.get_title()
        assert len(obj.get_columns()) == 5

        entry = ColumnListBoxEntry(obj)
        entry.get_next_view()
        entry.get_details_view()
        entry.search_match('')

        if obj.type in ['blogpost', 'page']:
            p = PageView(obj)
            p.go_to_comments()
        elif obj.type == 'comment':
            SingleCommentView(obj)

    obj = Generic(results[0])
    assert obj.get_title() is not None

    for record in caplog.records:
        assert record.levelname not in ['ERROR', 'CRITICAL']


def test_comments(load_comments, caplog, monkeypatch):
    # make sure that no requests are made, ever
    import requests

    def mock_request(*args, **kwargs):
        raise RuntimeError("Unable to make requests in test mode")
    monkeypatch.setattr(requests.Session,
                        "request",
                        mock_request)

    from congruence.args import load_config
    load_config(args=['--config', './config.yaml.sample'])

    from congruence.confluence import CommentContextView
    import congruence.confluence
    import congruence.objects
    import congruence.environment

    from congruence.app import app
    app.main(dummy=True)

    # Load comments from file
    comments = load_comments
    for c in comments:
        def mock_get_comments(*args, **kwargs):
            return json.dumps(c)

        def mock_get_long_input(*args, **kwargs):
            return 'foo'

        def mock_send_reply(*args, **kwargs):
            return True

        class MockObject(object):
            id = '0'
            title = 'Test'
            obj = None

            def send_reply(self, *args, **kwargs):
                pass

        monkeypatch.setattr(congruence.confluence,
                            "get_comments_of_page",
                            mock_get_comments)

        # Test reply function
        monkeypatch.setattr(congruence.environment.app,
                            "get_long_input",
                            mock_get_long_input)
        monkeypatch.setattr(congruence.objects.Comment,
                            "send_reply",
                            mock_send_reply)
        monkeypatch.setattr(congruence.confluence,
                            "post_comment",
                            mock_send_reply)

        CV = CommentContextView('0', MockObject())
        CV.reply()

    for record in caplog.records:
        assert record.levelname not in ['ERROR', 'CRITICAL']
