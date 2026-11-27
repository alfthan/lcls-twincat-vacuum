"""Helper for task #136: apply exact-substring edits to TwinCAT XML files.

Reads a file as utf-8-sig, normalises CRLF to LF, applies the edits, then
writes it back with BOM + CRLF.
"""
import re


def load(path):
    raw = open(path, 'rb').read()
    had_bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    return text, had_bom


def save(path, text, had_bom=True):
    out = text.replace('\r\n', '\n').replace('\n', '\r\n')
    data = out.encode('utf-8')
    if had_bom:
        data = b'\xef\xbb\xbf' + data
    open(path, 'wb').write(data)


def replace_once(text, old, new):
    n = text.count(old)
    if n != 1:
        raise SystemExit('pattern found %d times:\n%r' % (n, old[:300]))
    return text.replace(old, new)


def qualify_map(text, mapping):
    """Replace bare references of each key with its replacement, skipping ones
    that are already qualified (`x.name`, `This^.x.name`)."""
    for name, replacement in mapping.items():
        pattern = re.compile(r'(?<![\w.])' + re.escape(name) + r'\b')
        text = pattern.sub(replacement, text)
    return text


def qualify(text, prefix, names):
    """Prefix bare references of `names` with `prefix`, skipping ones already
    qualified as `prefix` or `This^.prefix` or `<something>.` + name."""
    for name in names:
        pattern = re.compile(r'(?<![\w.])' + re.escape(name) + r'\b')
        text = pattern.sub(prefix + name, text)
    return text


def apply(path, fn):
    text, had_bom = load(path)
    text = fn(text)
    save(path, text, had_bom)
    print('patched %s' % path)
