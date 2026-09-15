import re
from datetime import datetime

MONTHS={m:i for i,m in enumerate(('jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'),1)}
DATE_PATTERNS=[re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b'),re.compile(r'\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b',re.I),re.compile(r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b')]
FIELD_LABELS={
 'department':('department','ministry','organization/department','department name'),
 'vacancies':('total vacancies','number of vacancies','vacancy','vacancies','total posts','posts'),
 'qualification':('educational qualification','qualification','eligibility','educational eligibility'),
 'ageLimit':('age limit','maximum age','upper age','minimum age','age limit as on'),
 'applicationStartDate':('application start date','starting date','start date','online application starts','online application start'),
 'applicationLastDate':('last date','closing date','last date to apply','application last date','last date for application','online application ends'),
 'examDate':('exam date','examination date','date of examination','exam schedule'),
 'fee':('application fee','exam fee','examination fee','fee details','application fees','fee'),
 'ageRelaxation':('age relaxation','age relaxation applicable','relaxation in age'),
 'selectionProcess':('selection process','mode of selection','selection procedure','selection criteria'),
 'salary':('salary','pay scale','pay level','pay matrix','emoluments','remuneration','stipend'),
 'howToApply':('how to apply','application process','apply online','how can i apply'),
 'documentsRequired':('documents required','required documents','documents to upload','documents'),
 'jobLocation':('job location','place of posting','posting location','location'),
 'applicationMode':('application mode','mode of application'),
}
SECTION_HEADINGS=('important dates','eligibility','eligibility criteria','vacancy details','post details','important links','selection process','salary','pay scale','how to apply','documents required','documents to upload','age relaxation','application fee','exam date','job location','application mode','educational qualification')
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
 ('admission',r'\b(admission|entrance|college admission|university admission|admission form)\b'),
 ('syllabus',r'\b(syllabus|exam pattern|exam resources)\b'),
 ('notice',r'\b(corrigendum|addendum|important notice|public notice|advisory)\b'),
)

def clean(value):
    value=re.sub(r'\s+',' ',str(value or '')).strip(' :|-')
    value=re.sub(r'\s+([,.;:])',r'\1',value)
    return value

def classify_update_type(title,text=''):
    hay=clean((title or '')+' '+(text or ''))
    for category,pattern in CATEGORY_RULES:
        if re.search(pattern,hay,re.I): return category
    return 'jobs'

def normalized_date(value):
    value=clean(value)
    for p in DATE_PATTERNS:
        m=p.search(value)
        if not m: continue
        try:
            if m.group(1).isdigit() and len(m.group(1))==4:
                y,mo,d=map(int,m.groups()); return datetime(y,mo,d).strftime('%Y-%m-%d')
            if m.group(2).isdigit():
                d,mo,y=map(int,m.groups()); return datetime(y,mo,d).strftime('%Y-%m-%d')
            d,month,y=m.groups(); return datetime(int(y),MONTHS[month[:3].lower()],int(d)).strftime('%Y-%m-%d')
        except ValueError: pass
    return None

def _label_regex(labels): return '(?:'+'|'.join(re.escape(x) for x in sorted(set(labels),key=len,reverse=True))+')'

def extract_section(text,labels,stop_labels=(),max_len=900):
    text=clean(text)
    if not text:return None
    start_re=_label_regex(labels)
    stop_re=_label_regex(stop_labels) if stop_labels else ''
    pattern=r'(?is)(?<![A-Za-z])'+start_re+r'(?![A-Za-z])\s*[:\-]?\s*(.*?)'
    if stop_re: pattern+=r'(?=\s+(?:'+stop_re+r')\b|$)'
    else: pattern+=r'(?=$)'
    m=re.search(pattern,text)
    if not m:return None
    value=clean(m.group(1))
    if not value:return None
    return value[:max_len]

def _all_stop_labels(extra=()):
    out=list(SECTION_HEADINGS)+list(extra)
    for vals in FIELD_LABELS.values():out.extend(vals)
    return out

def extract_after_label(text,labels,max_len=700): return extract_section(text,labels,_all_stop_labels(),max_len)

def extract_dates(text):
    found=[]
    for p in DATE_PATTERNS:
        for m in p.finditer(text or ''):
            raw=m.group(0); iso=normalized_date(raw)
            if iso and iso not in [x['date'] for x in found]: found.append({'raw':raw,'date':iso})
    return found

def extract_vacancies(text):
    text=text or ''
    patterns=[r'(?i)(?:total\s+)?vacanc(?:y|ies)\s*[:\-]?\s*([\d,]+)',r'(?i)([\d,]+)\s+(?:posts?|vacancies)\b',r'(?i)(?:total\s+posts?)\s*[:\-]?\s*([\d,]+)']
    for p in patterns:
        m=re.search(p,text)
        if m:
            value=(m.group(1) or '').replace(',','').strip()
            if value.isdigit(): return int(value)
    return None

def extract_table_like(text,patterns,max_len=1600):
    for p in patterns:
        m=re.search(p,text or '',re.I|re.S)
        if m:
            value=clean(m.group(1))
            if value:return value[:max_len]
    return None

def normalize_record(raw):
    text=raw.get('text') or ''; title=clean(raw.get('title')); dates=extract_dates(text); stops=_all_stop_labels()
    last=extract_section(text,FIELD_LABELS['applicationLastDate'],stops); start=extract_section(text,FIELD_LABELS['applicationStartDate'],stops); exam=extract_section(text,FIELD_LABELS['examDate'],stops)
    fee=clean(raw.get('fee')) or extract_section(text,FIELD_LABELS['fee'],stops)
    age_relax=clean(raw.get('ageRelaxation')) or extract_section(text,FIELD_LABELS['ageRelaxation'],stops)
    age=clean(raw.get('ageLimit')) or extract_section(text,FIELD_LABELS['ageLimit'],stops)
    selection=clean(raw.get('selectionProcess') or raw.get('selection')) or extract_section(text,FIELD_LABELS['selectionProcess'],stops)
    salary=clean(raw.get('salary') or raw.get('payScale')) or extract_section(text,FIELD_LABELS['salary'],stops)
    how=clean(raw.get('howToApply')) or extract_section(text,FIELD_LABELS['howToApply'],stops)
    docs=clean(raw.get('documentsRequired')) or extract_section(text,FIELD_LABELS['documentsRequired'],stops)
    location=clean(raw.get('jobLocation')) or extract_section(text,FIELD_LABELS['jobLocation'],stops)
    mode=clean(raw.get('applicationMode')) or extract_section(text,FIELD_LABELS['applicationMode'],stops)
    qualification=clean(raw.get('qualification')) or extract_section(text,FIELD_LABELS['qualification'],stops)
    department=clean(raw.get('department')) or extract_section(text,FIELD_LABELS['department'],stops)
    category=clean(raw.get('category')) or classify_update_type(title,text)
    vacancy_details=clean(raw.get('vacancyDetails')) or extract_table_like(text,[r'(?i)(?:vacancy|post)\s+(?:details|details\s+and\s+vacancies)\s*[:\-]?\s*(.{20,1600})'])
    record={'title':title or clean(raw.get('jobTitle')),'department':department,'organization':clean(raw.get('organization')),'state':clean(raw.get('state')),'jobType':clean(raw.get('jobType')) or 'Government Job','category':category,'updateType':classify_update_type(title,text),'vacancies':raw.get('vacancies') or extract_vacancies(text),'vacancyDetails':vacancy_details,'qualification':qualification,'ageLimit':age,'ageRelaxation':age_relax,'fee':fee,'selectionProcess':selection,'selection':selection,'salary':salary,'payScale':salary,'howToApply':how,'documentsRequired':docs,'jobLocation':location,'applicationMode':mode,'applicationStartDate':normalized_date(start) if start else None,'applicationLastDate':normalized_date(last) if last else None,'examDate':normalized_date(exam) if exam else None,'notificationUrl':clean(raw.get('notificationUrl')),'applyUrl':clean(raw.get('applyUrl')),'source':clean(raw.get('source')) or 'MultiSource'}
    if not record['applicationLastDate'] and dates: record['applicationLastDate']=dates[-1]['date']
    record['dateEvidence']=dates
    return record

if __name__=='__main__': print('Government Update Field Extraction & Classification Engine: READY')
