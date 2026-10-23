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
CONFIG = json.loads((ROOT/'references/template-config.json').read_text())
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

def title_style(ref):
    style=copy.deepcopy(ref.find('p:txBody/a:lstStyle/a:lvl1pPr/a:defRPr',NS))
    style.tag=tag('a:rPr');style.set('sz',str(CONFIG['title_size']))
    return style

def standard_title(s, text, ref):
    # Copy new reference typography; downstream authoring may reposition the title.
    for child in ['p:spPr','p:txBody']:
        old=s.find(child,NS)
        if old is not None:s.remove(old)
        s.append(copy.deepcopy(ref.find(child,NS)))
    s.find('p:nvSpPr/p:cNvPr',NS).set('name','ESIGN_TITLE')
    text_shape(s,text)
    for para in s.findall('p:txBody/a:p',NS):
        for run in para.findall('a:r',NS):
            old=run.find('a:rPr',NS)
            if old is not None:run.remove(old)
            run.insert(0,title_style(ref))
        end=para.find('a:endParaRPr',NS)
        if end is not None:para.remove(end)


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
    ct=xml(data['[Content_Types].xml']);title_ref=shapes(xml(src[f"ppt/slides/slide{CONFIG['title_slide']}.xml"]))[CONFIG['title_shape_id']]
    # Keep one actual master in the output; the retained reference remains untouched.
    master_ids={e.get('Id') for e in rel if e.get('Type').endswith('/slideMaster') and target('ppt/presentation.xml',e.get('Target'))!=CONFIG['master']}
    for e in list(rel):
        if e.get('Id') in master_ids:rel.remove(e)
    masters=pres.find('p:sldMasterIdLst',NS)
    if masters is not None:
        for e in list(masters):
            if e.get(tag('r:id')) in master_ids:masters.remove(e)
    used_ids={e.get('Id') for e in rel}; nextid=1000
    for i,item in enumerate(plan,1):
        sn=int(item['source'])
        if not 1<=sn<=len(SLOTS):raise ValueError('Invalid source page')
        blank=item.get('blank',False)
        if sn==1 and blank:raise ValueError('Cover cannot be blanked')
        if sn in CONFIG['noncanonical_sources'] and not blank:raise ValueError('Source uses another master; rebuild its composition with blank:true on the brand background')
        if SLOTS[sn-1]['requires_asset_review'] and sn!=1 and not blank and not item.get('allow_source_assets',False):
            raise ValueError(f'Page {sn} has source media; review suitability and set allow_source_assets:true or use blank:true')
        source=f'ppt/slides/slide{sn}.xml';r=xml(src[source])
        if sn!=1:
            bg=r.find('p:cSld/p:bg',NS)
            if bg is not None:r.find('p:cSld',NS).remove(bg)
            r.set('showMasterSp','1')
        if blank:
            tree=r.find('p:cSld/p:spTree',NS)
            for el in list(tree):
                if el.tag not in (tag('p:nvGrpSpPr'),tag('p:grpSpPr')):tree.remove(el)
            for el in list(r):
                if el.tag in (tag('p:timing'),tag('p:transition')):r.remove(el)
        ss=shapes(r)
        repl={str(k):v for k,v in item.get('replace',{}).items()}
        title_id=None if sn in (1,CONFIG['ending_slide']) and not blank else SLOTS[sn-1]['title_id']
        if sn!=1 and (sn!=CONFIG['ending_slide'] or blank) and (blank or title_id is None):
            new=copy.deepcopy(title_ref);title_id=str(max([int(e.get('id')) for e in r.findall('.//p:cNvPr',NS)]+[1])+1)
            new.find('p:nvSpPr/p:cNvPr',NS).set('id',title_id)
            r.find('p:cSld/p:spTree',NS).append(new);ss=shapes(r)
        if title_id:
            if not item.get('title'):raise ValueError(f'Page {i}: title required')
            repl[title_id]=item['title']
        keep=set(map(str,item.get('keep',[])))
        required={k for k,s in ss.items() if visible(s)}
        missing=required-set(repl)-keep
        if missing:raise ValueError(f'Page {i}: replace or explicitly keep text shapes {sorted(missing)}')
        if set(repl)-set(ss):raise ValueError(f'Page {i}: unknown shape IDs')
        if sn==1 and (set(repl)-set(CONFIG['cover_text_ids'])):raise ValueError('Only four cover text shapes may change')
        for k,v in repl.items():
            if k==title_id:standard_title(ss[k],v,title_ref)
            else:text_shape(ss[k],v)
        part=f'ppt/slides/generated{i}.xml';data[part]=dump(r)
        sr=xml(src[relpath(source)])
        if blank:
            for e in list(sr):
                if not e.get('Type').endswith('/slideLayout'):sr.remove(e)
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
    if e is None:return None
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
    for sid in CONFIG['cover_text_ids']:
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
    standard=shapes(xml(src[f"ppt/slides/slide{CONFIG['title_slide']}.xml"]))[CONFIG['title_shape_id']]
    expected_style=title_style(standard)
    masters=xml(data['ppt/presentation.xml']).find('p:sldMasterIdLst',NS)
    if masters is None or len(masters)!=1:errors.append('Output must use one master')
    for i,part in enumerate(parts):
        root=xml(data[part]);rels=xml(data[relpath(part)]);layouts=[x.get('Target') for x in rels if x.get('Type').endswith('/slideLayout')]
        expected=CONFIG['cover_layout'] if i==0 else CONFIG['content_layout']
        if layouts!=[expected]:errors.append(f'Page {i+1}: wrong layout')
        if i==0:continue
        if root.find('p:cSld/p:bg',NS) is not None or root.get('showMasterSp')=='0':errors.append(f'Page {i+1}: background override')
        ss=shapes(root)
        # Closing-page exception only when the original layout/objects/text styles are retained.
        ending=xml(src[f"ppt/slides/slide{CONFIG['ending_slide']}.xml"])
        ending.set('showMasterSp','1')
        if strip_text(root)==strip_text(ending):
            es=shapes(ending)
            for sid,shape in ss.items():
                allowed={type_signature(x) for x in es[sid].findall('.//a:rPr',NS)}
                if any(type_signature(x) not in allowed for x in shape.findall('.//a:rPr',NS)):errors.append(f'Page {i+1}: closing text style changed')
            continue
        ts=[s for s in ss.values() if s.find('p:nvSpPr/p:cNvPr',NS).get('name')=='ESIGN_TITLE']
        if len(ts)!=1:errors.append(f'Page {i+1}: require one ESIGN_TITLE text box');continue
        runs=ts[0].findall('p:txBody/a:p/a:r/a:rPr',NS)
        if not runs:errors.append(f'Page {i+1}: empty title')
        for sty in runs:
            if sty.get('sz')!=str(CONFIG['title_size']) or sty.get('b')!='1':errors.append(f'Page {i+1}: title must be bold 30pt')
            for child in ['a:latin','a:ea','a:cs','a:gradFill']:
                if canonical(sty.find(child,NS))!=canonical(expected_style.find(child,NS)):errors.append(f'Page {i+1}: title font/gradient changed')
            if sty.find('a:solidFill',NS) is not None:errors.append(f'Page {i+1}: solid title fill')
    # Shared layout bytes and their full dependency closure must remain intact.
    layout='ppt/slideLayouts/slideLayout2.xml'
    for asset in {layout}|asset_closure(src,layout):
        if data.get(asset)!=src[asset]:errors.append('Shared background asset changed: '+asset)
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
