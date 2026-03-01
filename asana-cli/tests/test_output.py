import json

from asana_cli.output import output, output_error


def test_output_compact(capsys):
    output({"gid": "123", "name": "Test"})
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"gid": "123", "name": "Test"}
    assert "\n" not in captured.out.strip() or captured.out.count("\n") == 1


def test_output_pretty(capsys):
    output({"gid": "123"}, pretty=True)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"gid": "123"}
    # Pretty output has indentation
    assert "  " in captured.out


def test_output_list(capsys):
    output([{"gid": "1"}, {"gid": "2"}])
    captured = capsys.readouterr()
    assert json.loads(captured.out) == [{"gid": "1"}, {"gid": "2"}]


def test_output_error(capsys):
    output_error("something broke")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"error": "something broke"}
