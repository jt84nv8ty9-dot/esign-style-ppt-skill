#!/usr/bin/env python3
"""Clone source slides, replace editable text, preserve all untouched OOXML assets.
Python 3.9+, standard library only. Input source is always read-only.
"""
import argparse, copy, json, posixpath, sys, zipfile
from pathlib import Path
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[1]
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'rel':'http://schemas.openxmlformats.org/package/2006/relationships'}
for k,v in NS.items(): E.register_namespace(k,v)
A,P,R = [NS[k] for k in ('a','p','r')]
SLOTS = json.loads((ROOT/'references/slots.json').read_text())
def tag(n): return '{'+NS[n.split(':')[0]]+'}'+n.split(':')[1]
def xml(b): return E.fromstring(b)
def dump(e):
    if e.tag.endswith('}Types'): E.register_namespace('', 'http://schemas.openxmlformats.org/package/2006/content-types')
    elif e.tag.endswith('}Relationships'): E.register_namespace('', NS['rel'])
    return E.tostring(e,encoding='utf-8',xml_declaration=True)
def package(p):
    with zipfile.ZipFile(p) as z: return {n:z.read(n) for n in z.namelist() if not n.endswith('/')}
def shapes(r): return {s.find('p:nvSpPr/p:cNvPr',NS).get('id'):s for s in r.findall('.//p:sp',NS)}
def visible(s): return ''.join(t.text or '' for t in s.iter(tag('a:t')))
def text_shape(s, value):
    """String or paragraph array. Clone source paragraph/run style, avoid run-level hard breaks."""
    body=s.find('p:txBody',NS)
    if body is None: raise ValueError('Shape has no text body')
    pars=body.findall('a:p',NS)
    if not pars: raise ValueError('No source paragraphs')
    lines=value if isinstance(value,list) else str(value).split('\n')
    if not all(isinstance(x,str) for x in lines): raise ValueError('Text must be string or string array')
    for p in pars: body.remove(p)
    for i,line in enumerate(lines):
        old=pars[min(i,len(pars)-1)]; p=copy.deepcopy(old)
        style=old.find('a:r/a:rPr',NS)
        if style is None: style=old.find('a:pPr/a:defRPr',NS)
        for e in list(p):
            if e.tag not in [tag('a:pPr'),tag('a:endParaRPr')]: p.remove(e)
        end=p.find('a:endParaRPr',NS)
        r=E.Element(tag('a:r'))
        if style is not None:
            st=copy.deepcopy(style); st.tag=tag('a:rPr');r.append(st)
        E.SubElement(r,tag('a:t')).text=line
        p.insert(list(p).index(end) if end is not None else len(p),r);body.append(p)

def standard_title(s, text, ref):
    # Copy the source page 4 title's complete inherited typography and geometry.
    for child in ['p:spPr','p:txBody']:
        old=s.find(child,NS); idx=list(s).index(old);s.remove(old);s.insert(idx,copy.deepcopy(ref.find(child,NS)))
    text_shape(s,text)
    for st in s.findall('.//a:rPr',NS): st.set('sz','3000')
    # Standard title must remain a one-line editable title. Copy exactly, don't autofit down.

def relpath(part): return posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
def target(part,t): return posixpath.normpath(posixpath.join(posixpath.dirname(part),t)).lstrip('/')
def prune(data):
    keep={'[Content_Types].xml','_rels/.rels'}; todo=['']
    while todo:
        p=todo.pop();rp=relpath(p) if p else '_rels/.rels'
        if rp not in data:continue
        keep.add(rp)
        for r in xml(data[rp]):
            if r.get('TargetMode')=='External':continue
            dest=target(p,r.get('Target'))
            if dest not in data:raise ValueError('Dangling relationship: '+dest)
            if dest not in keep:keep.add(dest);todo.append(dest)
    ct=xml(data['[Content_Types].xml'])
    for e in list(ct):
        if e.get('PartName') and e.get('PartName').lstrip('/') not in keep:ct.remove(e)
    data['[Content_Types].xml']=dump(ct)
    return {k:v for k,v in data.items() if k in keep}

def build(specpath,output):
    spec=json.loads(Path(specpath).read_text());out=Path(output)
    if out.exists():raise ValueError('Refusing to overwrite an existing output')
    src=package(ROOT/'assets/reference.pptx');data=dict(src)
    plan=spec['slides']
    if not plan or plan[0]['source']!=1:raise ValueError('First page must reuse source cover 1')
    if any(p['source']==1 for p in plan[1:]):raise ValueError('Cover may only appear first')
    pres=xml(data['ppt/presentation.xml']);lst=pres.find('p:sldIdLst',NS);lst.clear()
    for e in list(pres):
        if e.tag==tag('p:custShowLst'):pres.remove(e)
    rel=xml(data['ppt/_rels/presentation.xml.rels'])
    for e in list(rel):
        if e.get('Type').endswith('/slide'):rel.remove(e)
    ct=xml(data['[Content_Types].xml']);title_ref=shapes(xml(src['ppt/slides/slide4.xml']))['10']
    used_ids={e.get('Id') for e in rel}; nextid=1000
    for i,item in enumerate(plan,1):
        sn=int(item['source'])
        if not 1<=sn<=18:raise ValueError('Source page must be 1..18')
        if sn in (2,3,6) and not item.get('allow_source_assets',False):
            raise ValueError(f'Page {sn} includes business images/charts/video; explicitly decide reuse first')
        source=f'ppt/slides/slide{sn}.xml';r=xml(src[source]);ss=shapes(r)
        repl={str(k):v for k,v in item.get('replace',{}).items()}
        title_id=SLOTS[sn-1]['title_id']
        if title_id:
            if not item.get('title'):raise ValueError(f'Page {i}: title required')
            repl[title_id]=item['title']
        keep=set(map(str,item.get('keep',[])))
        required={k for k,s in ss.items() if visible(s)}
        missing=required-set(repl)-keep
        if missing:raise ValueError(f'Page {i}: replace or explicitly keep text shapes {sorted(missing)}')
        if set(repl)-set(ss):raise ValueError(f'Page {i}: unknown shape IDs')
        if sn==1 and (set(repl)-{'3','4','6','7'}):raise ValueError('Only four cover text shapes may change')
        for k,v in repl.items():
            if k==title_id:standard_title(ss[k],v,title_ref)
            else:text_shape(ss[k],v)
        part=f'ppt/slides/generated{i}.xml';data[part]=dump(r)
        sr=xml(src[relpath(source)])
        for e in list(sr):
            if e.get('Type').endswith('/notesSlide'):sr.remove(e)
            if e.get('Type').endswith('/slideLayout'):
                e.set('Target','../slideLayouts/slideLayout1.xml' if sn==1 else '../slideLayouts/slideLayout2.xml')
        data[relpath(part)]=dump(sr)
        while f'rId{nextid}' in used_ids:nextid+=1
        rid=f'rId{nextid}';used_ids.add(rid);nextid+=1
        E.SubElement(rel,'{'+NS['rel']+'}Relationship',Id=rid,Type=R+'/slide',Target=f'slides/generated{i}.xml')
        E.SubElement(lst,tag('p:sldId'),{'id':str(500+i),tag('r:id'):rid})
        E.SubElement(ct,'{http://schemas.openxmlformats.org/package/2006/content-types}Override',PartName='/'+part,ContentType='application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
    data['ppt/presentation.xml']=dump(pres);data['ppt/_rels/presentation.xml.rels']=dump(rel);data['[Content_Types].xml']=dump(ct)
    data=prune(data)
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for k,v in data.items():z.writestr(k,v)
    print(json.dumps({'output':str(out.resolve()),'slides':len(plan)},ensure_ascii=False))

def canonical(e):
    return (e.tag,tuple(sorted(e.attrib.items())),e.text or '',tuple(canonical(x) for x in e))
def type_signature(e):
    e=copy.deepcopy(e)
    for k in ['lang','altLang','dirty','err','smtClean']:e.attrib.pop(k,None)
    return canonical(e)
def strip_text(r):
    r=copy.deepcopy(r)
    for s in r.findall('.//p:sp',NS):
        tb=s.find('p:txBody',NS)
        if tb is not None:s.remove(tb)
    return canonical(r)
def ordered_parts(data):
    rs={e.get('Id'):e.get('Target') for e in xml(data['ppt/_rels/presentation.xml.rels'])}
    return [target('ppt/presentation.xml',rs[e.get(tag('r:id'))]) for e in xml(data['ppt/presentation.xml']).find('p:sldIdLst',NS)]
def asset_closure(data,part,seen=None):
    seen=set() if seen is None else seen
    rp=relpath(part)
    if rp not in data:return seen
    for rel in xml(data[rp]):
        if rel.get('TargetMode')=='External':continue
        if rel.get('Type').endswith(('/notesSlide','/slide')):continue
        t=target(part,rel.get('Target'))
        if t not in seen:seen.add(t);asset_closure(data,t,seen)
    return seen

def audit(pptx):
    src=package(ROOT/'assets/reference.pptx');data=package(pptx);parts=ordered_parts(data);errors=[]
    if xml(data['ppt/presentation.xml']).find('p:sldSz',NS).attrib != xml(src['ppt/presentation.xml']).find('p:sldSz',NS).attrib:errors.append('Slide dimensions changed')
    if strip_text(xml(src['ppt/slides/slide1.xml']))!=strip_text(xml(data[parts[0]])):errors.append('Cover non-text objects changed')
    # Cover typography/boxes must remain source styles even though paragraphs can change.
    cs,ds=shapes(xml(src['ppt/slides/slide1.xml'])),shapes(xml(data[parts[0]]))
    for sid in ['3','4','6','7']:
        if sid not in ds:errors.append('Missing cover field '+sid);continue
        for path in ['p:txBody/a:bodyPr','p:txBody/a:lstStyle']:
            if canonical(cs[sid].find(path,NS))!=canonical(ds[sid].find(path,NS)):errors.append('Cover text style changed '+sid)
        allowed={type_signature(x) for x in cs[sid].findall('.//a:rPr',NS)}
        for sty in ds[sid].findall('.//a:rPr',NS):
            if type_signature(sty) not in allowed:errors.append('Cover typography changed '+sid)
    def media_rels(b):
        return sorted(tuple(sorted(x.attrib.items())) for x in xml(b) if not x.get('Type').endswith('/notesSlide'))
    if media_rels(src[relpath('ppt/slides/slide1.xml')])!=media_rels(data[relpath(parts[0])]):errors.append('Cover relationships changed')
    for part in asset_closure(src,'ppt/slides/slide1.xml'):
        if data.get(part)!=src[part]:errors.append('Cover/master asset changed: '+part)
    standard=shapes(xml(src['ppt/slides/slide4.xml']))['10']
    st=standard.find('p:txBody/a:lstStyle',NS)
    for i,part in enumerate(parts):
        root=xml(data[part]);rels=xml(data[relpath(part)]);layouts=[x.get('Target') for x in rels if x.get('Type').endswith('/slideLayout')]
        expected='../slideLayouts/slideLayout1.xml' if i==0 else '../slideLayouts/slideLayout2.xml'
        if layouts!=[expected]:errors.append(f'Page {i+1}: wrong layout')
        if i==0:continue
        ending=strip_text(root)==strip_text(xml(src['ppt/slides/slide18.xml']))
        if ending:continue
        ts=[s for s in shapes(root).values() if s.find('p:txBody/a:lstStyle',NS) is not None and canonical(s.find('p:txBody/a:lstStyle',NS))==canonical(st)]
        if len(ts)!=1:errors.append(f'Page {i+1}: missing/duplicate canonical title');continue
        if any(x.get('sz')!='3000' for x in ts[0].findall('.//a:rPr',NS)):errors.append(f'Page {i+1}: title must be 30pt')
    try:prune(dict(data))
    except ValueError as e:errors.append(str(e))
    report={'passed':not errors,'pages':len(parts),'errors':errors,'limits':'Structural checks only. Render every slide for text fit; verify facts and font availability separately.'}
    print(json.dumps(report,ensure_ascii=False,indent=2));return not errors

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('slots');p.add_argument('--slide',type=int)
    p=sub.add_parser('build');p.add_argument('spec');p.add_argument('output')
    p=sub.add_parser('audit');p.add_argument('pptx')
    a=ap.parse_args()
    if a.command=='slots':print(json.dumps(SLOTS[a.slide-1] if a.slide else SLOTS,ensure_ascii=False,indent=2))
    elif a.command=='build':build(a.spec,a.output)
    elif not audit(a.pptx):sys.exit(1)
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,IndexError) as e:sys.exit(str(e))
