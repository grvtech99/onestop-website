#!/usr/bin/env python3
"""Publish one verified government update after an explicitly approved PR merge.

Safety rules:
- only a verified, awaiting-final-approval payload is accepted
- the exact public update title must not already exist in the data layer
- the category block must be found exactly once
- the public data file is updated deterministically
"""
import json, re, sys

DATA_FILE='onestop-updates-data.js'
REQUIRED=['category','title','meta','url','vacancy','dates','eligibility','fee','age','selection','noticeUrl','applyUrl']
ALLOWED={'jobs','admit','results','answer','admission','scholarship','syllabus','important','local'}


def fail(msg):
    print('ERROR: '+msg, file=sys.stderr)
    return 2


def js(s):
    return json.dumps(str(s), ensure_ascii=False)


def main():
    if len(sys.argv) != 2:
        return fail('Usage: publish-approved-government-update.py <publication-payload.json>')
    path=sys.argv[1]
    with open(path, encoding='utf-8') as f:
        d=json.load(f)

    if d.get('reviewStatus') != 'verified':
        return fail('Payload is not verified.')
    if d.get('publicationStatus') != 'awaiting-final-approval':
        return fail('Payload is not awaiting final approval.')
    missing=[k for k in REQUIRED if not str(d.get(k,'')).strip()]
    if missing:
        return fail('Missing required fields: '+', '.join(missing))
    if d['category'] not in ALLOWED:
        return fail('Invalid category: '+str(d['category']))
    if not re.match(r'^https?://', str(d['url'])) or not re.match(r'^https?://', str(d['noticeUrl'])) or not re.match(r'^https?://', str(d['applyUrl'])):
        return fail('url, noticeUrl and applyUrl must be absolute http(s) URLs.')

    with open(DATA_FILE, encoding='utf-8') as f:
        source=f.read()

    title=str(d['title']).strip()
    # Check the exact title argument of a public d(...) record. This avoids
    # false positives when the title text merely appears inside another title,
    # a URL, or unrelated page text.
    exact_title=js(title)
    if re.search(r'\bd\(\s*'+re.escape(exact_title)+r'\s*,', source):
        return fail('Duplicate public update title already exists in '+DATA_FILE+': '+title)

    category=d['category']
    # Match the exact top-level category array in the current DATA object.
    pattern=r'(\n\s*'+re.escape(category)+r':\[\n)([\s\S]*?)(\n \],)'
    matches=list(re.finditer(pattern, source))
    if len(matches) != 1:
        return fail('Expected exactly one category block for '+category+', found '+str(len(matches))+'.')

    extra={
        'vacancy':d['vacancy'], 'dates':d['dates'], 'eligibility':d['eligibility'],
        'fee':d['fee'], 'age':d['age'], 'selection':d['selection'],
        'noticeUrl':d['noticeUrl'], 'applyUrl':d['applyUrl']
    }
    line="  d(%s,%s,%s,%s)," % (js(d['title']), js(d['meta']), js(d['url']), json.dumps(extra,ensure_ascii=False,separators=(',',':')))
    m=matches[0]
    new_source=source[:m.end(2)] + ('\n' if m.group(2) and not m.group(2).endswith('\n') else '') + line + source[m.end(2):]

    if new_source == source:
        return fail('No change produced.')
    with open(DATA_FILE,'w',encoding='utf-8') as f:
        f.write(new_source)
    print('Published: '+title)
    return 0

if __name__=='__main__':
    sys.exit(main())
