import re
from datetime import datetime

MONTHS={m:i for i,m in enumerate(('jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'),1)}
DATE_PATTERNS=[re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b'),re.compile(r'\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b',re.I)]
FIELD_LABELS={
 'department':('department','ministry','organization/department','department name'),
 'vacancies':('total vacancies','number of vacancies','vacancy','vacancies','posts'),
 'qualification':('educational qualification','qualification','eligibility'),
 'ageLimit':('age limit','maximum age','upper age','age'),
 'applicationStartDate':('application start date','starting date','start date','online application starts'),
 'applicationLastDate':('last date','closing date','last date to apply','application last date'),
 'examDate':('exam date','examination date','date of examination'),
}
CATEGORY_RULES=(
 ('admit_card',r'\b(admit card|e-admit|hall ticket|exam city|city intimation|call letter)\b'),
 ('result',r'\b(result|final result|score card|scorecard|marks)\b'),
 ('answer_key',r'\b(answer key|response sheet|provisional key|final key)\b'),
 ('cut_off',r'\b(cut.?off|cut off)\b'),
 ('merit_list',r'\b(merit list|selection list|shortlist|shortlisted)\b'),
 ('exam_schedule',r'\b(exam date|exam schedule|examination schedule|time table|timetable)\b'),
 ('document_verification',r'\b(document verification|certificate verification|dv schedule)\b'),
 ('counselling',r'\b(counselling|counseling|seat allotment)\b'),
 ('scholarship',r'\b(scholarship|fellowship|stipend)\b'),
 ('admission',r'\b(admission|entrance|application form|college admission|university admission)\b'),
 ('syllabus',r'\b(syllabus|exam pattern|exam resources)\b'),
 ('notice',r'\b(corrigendum|addendum|important notice|advisory|notification|notice)\b'),
)

def classify_update_type(title, text=''):
    hay=clean((title or '')+' '+(text or ''))
    for category,pattern in CATEGORY_RULES:
        if re.search(pattern,hay,re.I): return category
    return 'jobs'

def clean(value):
    return re.sub(r'\s+',' ',str(value or '')).strip(' :|-')

def normalized_date(value):
    value=clean(value)
    for p in DATE_PATTERNS:
        m=p.search(value)
        if m:
            try:
                if len(m.groups())==3 and m.group(2).isdigit():
                    d,mo,y=map(int,m.groups()); return datetime(y,mo,d).strftime('%Y-%m-%d')
                d,month,y=m.groups(); key=month[:3].lower(); return datetime(int(y),MONTHS[key],int(d)).strftime('%Y-%m-%d')
            except ValueError: pass
    return None

def extract_after_label(text,labels,max_len=500):
    lines=[clean(x) for x in text.splitlines() if clean(x)]
    low=[x.lower() for x in lines]
    for label in labels:
        for i,line in enumerate(low):
            if label in line:
                same=re.split(re.escape(label),lines[i],flags=re.I,maxsplit=1)
                value=clean(same[1] if len(same)>1 else '')
                if not value and i+1<len(lines): value=lines[i+1]
                if value: return value[:max_len]
    return None

def extract_dates(text):
    found=[]
    for p in DATE_PATTERNS:
        for m in p.finditer(text):
            raw=m.group(0); iso=normalized_date(raw)
            if iso and iso not in [x['date'] for x in found]: found.append({'raw':raw,'date':iso})
    return found

def extract_vacancies(text):
    m=re.search(r'(?i)(?:total\s+)?vacanc(?:y|ies)\s*[:\-]?\s*([\d,]*)',text or '')
    if not m: m=re.search(r'(?i)([\d,]+)\s+(?:posts?|vacancies)',text or '')
    value=(m.group(1) or '').replace(',','').strip() if m else ''
    return int(value) if value.isdigit() else None

def normalize_record(raw):
    text=raw.get('text') or ''
    title=clean(raw.get('title'))
    dates=extract_dates(text)
    last=extract_after_label(text,FIELD_LABELS['applicationLastDate'])
    start=extract_after_label(text,FIELD_LABELS['applicationStartDate'])
    exam=extract_after_label(text,FIELD_LABELS['examDate'])
    record={
      'title':title or clean(raw.get('jobTitle')),
      'department':clean(raw.get('department')) or extract_after_label(text,FIELD_LABELS['department']),
      'organization':clean(raw.get('organization')),
      'state':clean(raw.get('state')),
      'jobType':clean(raw.get('jobType')) or 'Government Job',
      'category':clean(raw.get('category')) or classify_update_type(title,text),
      'updateType':classify_update_type(title,text),
      'vacancies':raw.get('vacancies') or extract_vacancies(text),
      'qualification':clean(raw.get('qualification')) or extract_after_label(text,FIELD_LABELS['qualification']),
      'ageLimit':clean(raw.get('ageLimit')) or extract_after_label(text,FIELD_LABELS['ageLimit']),
      'applicationStartDate':normalized_date(start) if start else None,
      'applicationLastDate':normalized_date(last) if last else None,
      'examDate':normalized_date(exam) if exam else None,
      'notificationUrl':clean(raw.get('notificationUrl')),
      'applyUrl':clean(raw.get('applyUrl')),
      'source':clean(raw.get('source')) or 'MultiSource',
    }
    if not record['applicationLastDate'] and dates:
        record['applicationLastDate']=dates[-1]['date']
    record['dateEvidence']=dates
    return record

if __name__=='__main__':
    print('Government Update Field Extraction & Classification Engine: READY')
