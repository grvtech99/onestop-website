#!/usr/bin/env python3
"""Create a publication branch/PR from a verified government draft.

Usage:
  python3 scripts/create-government-publication-pr.py path/to/draft.json

The script never writes directly to main. It creates a branch and a PR that
adds a clearly marked publication payload for final human review. The actual
public data file is intentionally not modified automatically.
"""
import json, os, re, subprocess, sys

REPO=os.environ.get('GITHUB_REPOSITORY','grvtech99/onestop-website')
BASE=os.environ.get('BASE_BRANCH','main')


def run(*args):
    return subprocess.check_output(args,text=True).strip()


def main():
    if len(sys.argv)!=2:
        print('Usage: create-government-publication-pr.py <draft.json>',file=sys.stderr); return 2
    path=sys.argv[1]
    with open(path,encoding='utf-8') as f: d=json.load(f)
    if d.get('reviewStatus')!='verified':
        print('Draft is not verified.',file=sys.stderr); return 2
    required=['category','title','meta','url','vacancy','dates','eligibility','fee','age','selection','noticeUrl','applyUrl']
    missing=[k for k in required if not str(d.get(k,'')).strip()]
    if missing:
        print('Missing required fields: '+', '.join(missing),file=sys.stderr); return 2
    slug=re.sub(r'[^a-z0-9]+','-',str(d['title']).lower()).strip('-')[:50] or 'government-update'
    issue=str(d.get('verificationIssue','unknown'))
    branch=f'publish/government-update-{slug}-issue-{issue}'
    try: run('git','fetch','origin',BASE)
    except subprocess.CalledProcessError: pass
    run('git','checkout','-b',branch,f'origin/{BASE}')
    out='data/government-publication-review/'+slug+'-issue-'+issue+'.json'
    os.makedirs(os.path.dirname(out),exist_ok=True)
    payload=dict(d)
    payload['publicationStatus']='awaiting-final-approval'
    payload['publicationWarning']='FINAL REVIEW REQUIRED — this payload is not the public Job Update data.'
    with open(out,'w',encoding='utf-8') as f: json.dump(payload,f,indent=2,ensure_ascii=False); f.write('\n')
    run('git','add',out)
    run('git','config','user.name','github-actions[bot]')
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','commit','-m',f'Prepare government update for final publication: {d["title"]}')
    run('git','push','--set-upstream','origin',branch)
    pr=run('gh','pr','create','--repo',REPO,'--base',BASE,'--head',branch,'--title',f'Publish government update: {d["title"]}','--body',f'''## Final Publication Review\n\nThis PR was generated from verified draft **Issue #{issue}**.\n\n### Mandatory checks\n- [ ] Official notice re-opened and matched\n- [ ] Vacancy / post count confirmed\n- [ ] Important dates confirmed\n- [ ] Eligibility confirmed\n- [ ] Fee and age limit confirmed\n- [ ] Selection process confirmed\n- [ ] Official notice URL confirmed\n- [ ] Official application URL confirmed\n- [ ] Public wording reviewed\n\n**Important:** This PR intentionally does **not** modify `onestop-updates-data.js`. Final publication remains a separate, explicit approved change.\n''')
    print(pr)
    return 0

if __name__=='__main__': sys.exit(main())
