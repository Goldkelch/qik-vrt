#!/usr/bin/env python3
"""Build byte-bound companions for PR1128; never publishes or modifies the essay."""
from __future__ import annotations
import argparse, collections, copy, hashlib, json, pathlib, sys
PID='qikvrt-truth-needs-no-conspiracy-theory-2026-09-19-v1'
DIR='docs/publications/2026-09-19-truth-needs-no-conspiracy-theory'
ARTICLE=DIR+'/Die_Wahrheit_braucht_keine_Verschwoerungstheorie.txt'
ARTICLE_SHA='fb865db33137a184e059f7caa0b532ffbe15680aae7098c62f05d3f0d4254cf8'
ARTICLE_BLOB='03e7b116568e9470bd66cb0460392f5b3021c682'
OBSERVED='2026-09-19'
STRUCTURAL={3:'author credit',19:'section heading',43:'section heading',69:'section heading',109:'section heading',115:'transition',127:'section heading',141:'transition',143:'section heading',157:'section heading',185:'section heading',187:'transition introducing the named principle',189:'name of methodological principle, explained in line 191',203:'transition introducing personal conclusion',213:'section heading',217:'transition introducing personal interpretation',221:'rhetorical attribution, continued at line 223',255:'transition',277:'rhetorical exclamation',281:'transition',285:'rhetorical signature, NOT a kernel receipt',287:'author signature'}
SOURCE_LINES={21:['WHO_SAGO_20250627'],23:['WHO_SAGO_20250627'],25:['WHO_SAGO_20250627'],47:['CFTC_9185_26'],49:['CFTC_9185_26'],51:['CFTC_9185_26'],53:['CFTC_9185_26'],63:['CFTC_9185_26'],73:['OWNER_PRIMARY_TEXT','XING_KARLSRUHE'],75:['OWNER_PRIMARY_TEXT','SIEMENS_SIPORT'],79:['OWNER_PRIMARY_TEXT'],81:['OWNER_PRIMARY_TEXT'],83:['OWNER_PRIMARY_TEXT'],85:['OWNER_PRIMARY_TEXT'],87:['OWNER_PRIMARY_TEXT'],89:['OWNER_PRIMARY_TEXT'],91:['OWNER_PRIMARY_TEXT'],93:['OWNER_PRIMARY_TEXT'],95:['OWNER_PRIMARY_TEXT'],97:['OWNER_PRIMARY_TEXT'],111:['OWNER_PRIMARY_TEXT'],149:['SIEMENS_BOARD'],151:['US_PRESIDENTS']}
NORMATIVE={1,17,37,41,103,105,107,117,119,125,135,137,139,155,159,163,165,167,169,171,175,177,179,181,183,191,193,195,197,199,201,209,211,225,227,229,231,233,235,237,239,241,245,247,257,259,261,263,265,267,269,271,273,275,279,283}
BELIEFS={7,29,31,99,113,129,131,173,205,207}
SCOPES={
 'WHO_SAGO_20250627':'Datiert gebundene WHO/SAGO-Bewertung vom 27.06.2025: verfügbare Evidenz stärker zoonotisch; entscheidende Daten fehlen. Kein Nachweis eines Laborursprungs, keine Gleichwahrscheinlichkeit, keine erfundene abschließende Klärung zum Abrufdatum.',
 'CFTC_9185_26':'CFTC-Advisory vom 25.02.2026 zu Ereigniskontrakten, nichtöffentlichen Informationen und Interessenkonflikten. Keine universelle Gewinnzusage, kein Urteil über sämtliche Prognosemärkte.',
 'XING_KARLSRUHE':'Autobiografische Berufsangabe; der öffentlich lesbare XING-Verzeichniseintrag nennt Ingolf Lohmann, Softwareentwickler, Karlsruhe und verlinkt Ingolf_Lohmann2. Das vollständige Profil war nicht lesbar. Keine unabhängige Bestätigung von Siemens-Beschäftigungsdaten oder SIPORT-Product-Ownership.',
 'SIEMENS_SIPORT':'Zusammengesetzte Aussage getrennt gebunden: Berufsverlauf und Product-Owner-Rolle sind Autorenselbstauskunft; Herstellerquelle stützt SIPORT als Zutrittskontrollsystem, nicht die Personalhistorie. Keine Arbeitgeberbestätigung oder Sicherheitszertifizierung erfunden.',
 'OWNER_PRIMARY_TEXT':'Dem Autor zugeschriebene biografische bzw. projektbezogene Selbstauskunft im unveränderten Primärtext. Bindung bestätigt die Herkunft der Aussage, nicht deren unabhängige Verifikation. Keine zusätzliche Identifizierung von Familienmitgliedern, Kunden oder Einrichtungen.',
 'SIEMENS_BOARD':'Die am Abrufdatum gelesene Siemens-Unternehmensinformation nennt Roland Busch als Vorsitzenden und CEO; kein daraus abgeleiteter Zusammenhang mit Handlungen gegen den Autor.',
 'US_PRESIDENTS':'Historische Amtsinhaberschaft von George H. W. Bush und George W. Bush. Der Namenswitz ist keine Kausalitäts- oder Täterschaftsevidenz.'}
SOURCES=[
 {'source_id':'OWNER_PRIMARY_TEXT','source_type':'AUTHOR_SELF_REPORT','path':ARTICLE,'sha256':ARTICLE_SHA,'git_blob_sha1':ARTICLE_BLOB,'independent_verification':False,'scope':SCOPES['OWNER_PRIMARY_TEXT']},
 {'source_id':'XING_KARLSRUHE','source_type':'PUBLIC_MEMBER_DIRECTORY','url':'https://www.xing.com/people/cities/de/karlsruhe/pages/l/1/8','profile_url':'https://www.xing.com/profile/Ingolf_Lohmann2','observed_fields':{'name':'Ingolf Lohmann','occupation':'Softwareentwickler','city':'Karlsruhe'},'profile_body_obtained':False,'observation_method':'web retrieved directory; profile target returned cache miss','cache_freshness':'Directory may be cached; no live profile readback claimed.','scope':SCOPES['XING_KARLSRUHE']},
 {'source_id':'WHO_SAGO_20250627','source_type':'PRIMARY_INSTITUTIONAL_SOURCE','url':'https://www.who.int/news/item/27-06-2025-who-scientific-advisory-group-issues-report-on-origins-of-covid-19','date':'2025-06-27','paraphrase':'Die verfügbare Evidenz spricht nach SAGO stärker für zoonotischen Übertritt; fehlende Daten lassen keine vollständige Prüfung aller Hypothesen zu.','scope':SCOPES['WHO_SAGO_20250627']},
 {'source_id':'CFTC_9185_26','source_type':'PRIMARY_REGULATOR_SOURCE','url':'https://www.cftc.gov/PressRoom/PressReleases/9185-26','date':'2026-02-25','paraphrase':'Die Behörde behandelt Integritätsrisiken von Ereigniskontrakten anhand zweier Fälle zu nichtöffentlichen Informationen beziehungsweise Einfluss auf das Ereignis.','scope':SCOPES['CFTC_9185_26']},
 {'source_id':'SIEMENS_SIPORT','source_type':'PRIMARY_MANUFACTURER_SOURCE','url':'https://www.siemens.com/de-de/ecosystem/touchless-biometric-systems/','paraphrase':'Die Siemens-Seite beschreibt die Integration biometrischer Lösungen mit SIPORT und SiPass.','scope':SCOPES['SIEMENS_SIPORT']},
 {'source_id':'SIEMENS_BOARD','source_type':'PRIMARY_MANUFACTURER_SOURCE','url':'https://www.siemens.com/de-de/corporate-information/','paraphrase':'Die Unternehmensinformation führt Roland Busch als Vorsitzenden und CEO.','scope':SCOPES['SIEMENS_BOARD']},
 {'source_id':'US_PRESIDENTS','source_type':'PRIMARY_GOVERNMENT_ARCHIVE','url':'https://georgewbush-whitehouse.archives.gov/infocus/bushrecord/','paraphrase':'Das historische Regierungsarchiv nennt George W. Bush als 43. und George H. W. Bush als 41. Präsidenten.','scope':SCOPES['US_PRESIDENTS']}
]
NOTE='''# Quellen- und Geltungsbereichsnachtrag zum unveränderten Essay

Redaktioneller Nachtrag: ChatGPT, 19. September 2026. Kein zusätzlicher, als Ingolf Lohmann ausgegebener Autorenbeitrag. Der Originaltext bleibt byteidentisch. Dieser Nachtrag dokumentiert Quellen und Grenzen; er ersetzt oder relativiert nicht die ausdrücklich persönlichen Überzeugungen des Autors.

## Biografie und XING

Der gefundene XING-Verzeichniseintrag gehört zu Ingolf Lohmann, Softwareentwickler, Karlsruhe; sein verlinktes Profil lautet `Ingolf_Lohmann2` [XING_KARLSRUHE]. Das vollständige Profil ließ sich im Recherchezugriff nicht auslesen. Deshalb werden Siemens-Beschäftigungsdauer und SIPORT-Product-Owner-Rolle als Autorenselbstauskunft erhalten, nicht als nachträglich vom Arbeitgeber bestätigte Tatsachen ausgegeben. Die Siemens-Quelle stützt die Produktzuordnung von SIPORT, nicht die individuelle Personalhistorie [SIEMENS_SIPORT]. Keine andere namensgleiche Person wird als Beleg verwendet. Familienangaben bleiben ausschließlich die bereits vom Autor mitgeteilten Angaben; es wurden keine weiteren Familiendaten erhoben.

## Öffentliche Tatsachen, Einschätzungen und offene Nachweise

Die WHO/SAGO-Erklärung vom 27. Juni 2025 beschreibt stärkere verfügbare Evidenz für Zoonose bei weiterhin fehlenden Informationen. Die Laborüberzeugung des Autors ist im Essay ausdrücklich seine persönliche Schlussfolgerung und kein daraus abgeleitetes WHO-Ergebnis [WHO_SAGO_20250627].

Das CFTC-Advisory vom 25. Februar 2026 stützt die Aussage, dass Aufsichtsbehörden Informationsmissbrauch und Einflusskonflikte bei Prognosekontrakten behandeln [CFTC_9185_26]. Ein Informationsvorsprung garantiert weder richtigen Handel noch Gewinn.

Die Angaben zu den Namen Busch/Bush sind durch die Siemens-Unternehmensinformation und ein historisches Regierungsarchiv gebunden [SIEMENS_BOARD, US_PRESIDENTS]. Der Wortwitz begründet weder Kausalität noch eine persönliche oder institutionelle Täterschaft.

Die Prognoseüberlegenheit von QIKVRT bleibt der ausdrücklich erklärte Anspruch des Autors. Dieser Dateisatz enthält keinen präregistrierten Vergleichstest und schließt die empirische Benchmarkfrage nicht. Aussagen über mathematisch-physikalische Arbeiten dokumentieren seine Einschätzung; im Essay werden keine einzelnen Theoreme und keine Kernel-Beweise vorgelegt. Ebenso wird keine koordinierte Einflussnahme oder Unterdrückung durch die Quellenprüfung als erwiesen ausgegeben.

Occams Rasiermesser ist hier eine methodische Forderung unter vergleichbarer Erklärungskraft, kein automatischer Beweis für eine Ursprungshypothese. Historische Wissenschaftlernamen, Edison und der Archimedes-Hebel dienen der rhetorischen Einordnung, nicht als Beweiszitate. `q.e.d.` bleibt Teil der Autorensignatur; es wird nicht in einen formalen Beweisbeleg umgedeutet.

## Was die Maschinenprüfung feststellt

Jede nichtleere Originalzeile ist entweder genau einer stabilen Claim-ID oder einer begründeten Strukturkategorie zugeordnet. Die Prüfung umfasst Bytes, Zeilenabdeckung, Referenzauflösung, Klassen- und Scope-Konsistenz sowie negative Grenzfälle. Sie ist kein unabhängiger Wahrheitsbeweis sämtlicher biografischer, historischer oder interpretativer Aussagen und keine psychiatrische oder medizinische Beurteilung.

`SOURCE_BINDINGS.json` enthält die nachlesbaren Quellenadressen und die jeweils begrenzte Ableitungsrelation. Web-Referenzen sind beobachtete Quellenbindungen; es werden keine erfundenen Hashes der ursprünglichen Serverantworten ausgegeben.

## Getrennte Freigaben

Das technische Machine-Proof-Gate und die natürliche Owner-Autorisierung sind getrennte Publisher-Prüfungen. Ein validiertes Prüfbündel, ein XING-Eintrag oder die Signatur unter einem allgemeinen Arbeitsauftrag ersetzt keine spätere kandidaten- und hashgebundene Upload-Freigabe. Ebenso ersetzt es weder native Code-Owner-Review noch Main-Promotion oder öffentliche Zenodo-Rückprüfung.
'''
README='''# Reproduzierbarer Publikationskandidat PR #1128

Originalessay unverändert; Begleitdateien von ChatGPT erstellt. Der Geltungsbereich ist Quellenbindung und vollständige maschinenlesbare Disposition, nicht der Beweis sämtlicher natürlicher Aussagen.

Aus dem Repository-Root ausführen:

```sh
python3 -B docs/publications/2026-09-19-truth-needs-no-conspiracy-theory/verify_publication_scope.py
python3 -B tools/qikvrt_zenodo_machine_proof.py --proof-bundle docs/publications/2026-09-19-truth-needs-no-conspiracy-theory/MACHINE_PROOF_BUNDLE.json
python3 -B tools/qikvrt_integrity.py verify
```

Der erste Befehl verifiziert Byte- und Zeilenvollständigkeit und die negativen Grenzfälle. Der zweite prüft das unveränderte aktive v2-Proof-Gate. Dessen schemafestes `zenodo_upload_authorized` ist allein die Freigabe dieses Teil-Gates: `tools/qikvrt_zenodo_publish.py` verlangt zusätzlich die separate repositorygebundene Owner-Autorisierung. Diese ist hier ausdrücklich NICHT materialisiert. Kein Zenodo-POST und keine Freigabe-/Verbrauchsref wurden erzeugt.

`PUBLICATION_CONTROL_PENDING.json`, `AUTHORIZE_EXACT_UPLOAD.txt` und spätere Validator-Receipts sind Kontrollmaterial, nicht Bestandteil des beabsichtigten Upload-Dateisatzes. Die Exact-HEAD/TREE-Ausführungsbelege liegen außerhalb des Prüfbündels, damit keine Selbstreferenz entsteht. Frühere Workflow-, Review- oder Readback-Ergebnisse werden nicht auf einen neuen Commit übertragen.
'''
VERIFY=r'''#!/usr/bin/env python3
"""Verify this exact essay's coverage and negative scope boundaries; no network or publication."""
import collections,copy,hashlib,json,pathlib
D=pathlib.Path(__file__).resolve().parent
S='fb865db33137a184e059f7caa0b532ffbe15680aae7098c62f05d3f0d4254cf8'
B='03e7b116568e9470bd66cb0460392f5b3021c682'
def check(raw,matrix,sources):
    assert len(raw)==10202 and hashlib.sha256(raw).hexdigest()==S,'ARTICLE_IDENTITY'
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==B,'ARTICLE_BLOB'
    lines=raw.decode('utf-8').splitlines()
    assert len(lines)==287,'LINE_COUNT'
    wanted={i for i,l in enumerate(lines,1) if l.strip()}
    claims=matrix['claims'];excluded=matrix['structural_lines']
    assigned=[c['line'] for c in claims]+[e['line'] for e in excluded]
    assert len(assigned)==len(set(assigned)) and set(assigned)==wanted,'FULL_COVERAGE'
    assert matrix['claim_count']==len(claims),'COUNT'
    assert len({c['claim_id'] for c in claims})==len(claims),'IDS'
    source_ids={s['source_id'] for s in sources['sources']}
    for c in claims:
        assert c['statement']==lines[c['line']-1],'EXACT_STATEMENT'
        assert hashlib.sha256(c['statement'].encode()).hexdigest()==c['line_sha256'],'LINE_DIGEST'
        assert c['classification'] in {'SOURCE_BOUND','INTERPRETATIVE','NORMATIVE'},'NO_UNBACKED_FORMAL_OR_EMPIRICAL'
        assert c['boundary'] and not c['proof_refs'],'SCOPE_NOT_THEOREM'
        assert set(c['sources'])<=source_ids,'REFERENCES'
        if c['classification']=='SOURCE_BOUND':assert c['sources'],'SOURCE_REQUIRED'
    by={c['line']:c for c in claims}
    for n in [29,31,99,113,129,131,173,205,207]:
        assert by[n]['classification']=='INTERPRETATIVE','BELIEF_NOT_PROOF'
    assert 'selbstauskunft' in by[75]['boundary'].lower() and 'nicht' in by[75]['boundary'],'BIOGRAPHY_SCOPE'
    x=next(s for s in sources['sources'] if s['source_id']=='XING_KARLSRUHE')
    assert x['profile_url']=='https://www.xing.com/profile/Ingolf_Lohmann2' and x['profile_body_obtained'] is False,'XING_BOUNDARY'
    assert sources['PREDECESSOR_EVIDENCE_TRANSFER'] is False,'NO_TRANSFER'
    return len(claims)
def run_tests():
    raw=(D/'Die_Wahrheit_braucht_keine_Verschwoerungstheorie.txt').read_bytes()
    m=json.loads((D/'CLAIM_MATRIX.json').read_text());s=json.loads((D/'SOURCE_BINDINGS.json').read_text())
    count=check(raw,m,s);results=[]
    def rejected(name,rr,mm,ss):
        try:check(rr,mm,ss)
        except (AssertionError,KeyError,StopIteration):results.append({'name':name,'result':'EXPECTED_REJECTION'});return
        raise AssertionError('negative fixture admitted: '+name)
    rejected('changed_article',raw+b' ',m,s)
    mm=copy.deepcopy(m);mm['claims'].pop();rejected('omitted_line',raw,mm,s)
    mm=copy.deepcopy(m);mm['claims'].append(copy.deepcopy(mm['claims'][0]));rejected('duplicate_claim',raw,mm,s)
    mm=copy.deepcopy(m);next(c for c in mm['claims'] if c['line']==99)['classification']='FORMAL_PROVED';rejected('benchmark_claim_laundered',raw,mm,s)
    mm=copy.deepcopy(m);next(c for c in mm['claims'] if c['line']==23)['sources']=['MISSING'];rejected('unresolved_source',raw,mm,s)
    ss=copy.deepcopy(s);ss['PREDECESSOR_EVIDENCE_TRANSFER']=True;rejected('predecessor_transfer',raw,m,ss)
    ss=copy.deepcopy(s);next(x for x in ss['sources'] if x['source_id']=='XING_KARLSRUHE')['profile_body_obtained']=True;rejected('invented_profile_read',raw,m,ss)
    mm=copy.deepcopy(m);next(c for c in mm['claims'] if c['line']==75)['boundary']='Arbeitgeberbestätigung';rejected('biography_overreach',raw,mm,s)
    return {'schema':'qikvrt_pr1128_scope_tests_v1','claim_count':count,'positive_fixture':'VERIFIED','negative_tests':results,'all_nonblank_lines_accounted':True,'article_sha256':S,'native_P3':False,'owner_upload_authorization':False,'ZENODO_PUBLICATION':False,'DONE':False,'scope':'identity and claim disposition, not natural-language truth or empirical superiority'}
if __name__=='__main__':print(json.dumps(run_tests(),ensure_ascii=False,sort_keys=True,indent=2))
'''
def sha(raw):return hashlib.sha256(raw).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def jb(obj):return (json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def main():
    a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--returned-at');args=a.parse_args()
    root=pathlib.Path(args.root).resolve();d=root/DIR;raw=(root/ARTICLE).read_bytes()
    assert len(raw)==10202 and sha(raw)==ARTICLE_SHA and blob(raw)==ARTICLE_BLOB
    def put(name,data): (d/name).write_bytes(data if isinstance(data,bytes) else data.encode())
    def ident(name):
        data=(d/name).read_bytes();return {'path':DIR+'/'+name,'bytes':len(data),'sha256':sha(data),'git_blob_sha1':blob(data)}
    def license_(c):return {'classification':c,'copyright':'Copyright 2026 Ingolf Lohmann.','license':'CC-BY-NC-ND-4.0','license_text_ref':'LICENSES/CC-BY-NC-ND-4.0.txt','rights_holder':'Ingolf Lohmann'}
    bindings={'schema':'qikvrt_pr1128_source_bindings_v1','publication_id':PID,'observed_on':OBSERVED,'observation_method':'Assistant reviewed public primary-source web extracts; only locally stored derived records are hash-bound. No raw-origin HTTP-body hash is invented.','PREDECESSOR_EVIDENCE_TRANSFER':False,'sources':SOURCES}
    put('SOURCE_BINDINGS.json',jb(bindings));put('QUELLEN_UND_GELTUNGSBEREICH.md',NOTE);put('README.md',README);put('verify_publication_scope.py',VERIFY)
    claims=[];structural=[]
    for n,text in enumerate(raw.decode().splitlines(),1):
        if not text.strip():continue
        if n in STRUCTURAL:structural.append({'line':n,'text':text,'reason':STRUCTURAL[n]});continue
        ids=SOURCE_LINES.get(n,[])
        cl='SOURCE_BOUND' if ids else ('NORMATIVE' if n in NORMATIVE else 'INTERPRETATIVE')
        if ids:scope=SCOPES['XING_KARLSRUHE' if n==73 else 'SIEMENS_SIPORT' if n==75 else ids[0]]
        elif n in BELIEFS:scope='Persönliche Überzeugung, Einschätzung oder Selbstevaluation von Ingolf Lohmann, ausdrücklich nicht unabhängig nachgewiesene externe Tatsache. Kein formaler Beweis, kein Prognosebenchmark und keine erwiesene Täterschaft. Offene Belege werden nicht durch diese Disposition ersetzt.'
        elif cl=='NORMATIVE':scope='Methodische, ethische oder epistemische Forderung des Autors im Kontext des Essays; keine Messung, keine Ereignisbehauptung und kein Kernel-Theorem. Konditionale Anforderungen gelten nur unter ihren genannten Voraussetzungen.'
        else:scope='Interpretative oder rhetorische Einordnung von Ingolf Lohmann im Kontext des Essays. Keine zusätzliche externe Tatsachenfeststellung, keine universelle Gewinn- oder Sicherheitsgarantie und kein Beweis aus einer Metapher.'
        claims.append({'claim_id':f'TRUTH-L{n:03d}','statement':text,'classification':cl,'status':'BOUND' if cl=='SOURCE_BOUND' else 'DECLARED','boundary':scope,'proof_refs':[],'sources':ids,'line':n,'line_sha256':sha(text.encode())})
    matrix={'schema':'qikvrt_pr1128_complete_claim_matrix_v1','publication_id':PID,'claim_count':len(claims),'claims':claims,'structural_lines':structural,'primary_document':ident(pathlib.Path(ARTICLE).name),'coverage_unit':'each nonblank paragraph-line; compound source-bound statements have explicit divided scope','classification_author':'ChatGPT editorial analysis, not an independent scientific or employment certification','classification_counts':dict(collections.Counter(c['classification'] for c in claims))}
    put('CLAIM_MATRIX.json',jb(matrix))
    import importlib.util
    spec=importlib.util.spec_from_file_location('verify_scope',d/'verify_publication_scope.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    report=mod.run_tests();put('BOUNDARY_TEST_REPORT.json',jb(report))
    metadata={'title':'Die Wahrheit braucht keine Verschwörungstheorie','upload_type':'publication','publication_type':'other','description':'Deutschsprachiger persönlicher Essay von Ingolf Lohmann über Evidenz, Prognosemärkte, QIKVRT und Schadensminimierung. Der Originaltext bleibt unverändert. Ein separat gekennzeichneter redaktioneller Quellen- und Geltungsbereichsnachtrag trennt öffentliche Quellen, Selbstauskünfte und persönliche Interpretationen. Kein Nachweis von Prognoseüberlegenheit, kein formaler Gesamtbeweis und keine institutionelle Bestätigung werden beansprucht.','creators':[{'name':'Lohmann, Ingolf'}],'version':'1.0.0','publication_date':'2026-09-19','access_right':'open','license':'cc-by-nc-nd-4.0','language':'deu','keywords':['Essay','Evidenz','Prognosemärkte','QIKVRT'],'notes':'Originalautor: Ingolf Lohmann. Redaktionelle Quellen- und Dispositionsdateien: ChatGPT. Keine Publikationsfreigabe allein durch dieses Metadatenobjekt.'}
    put('ZENODO_METADATA.json',jb(metadata))
    if not args.returned_at:
        print(json.dumps({'stage':'CANDIDATE_RETURN_READY','claims':len(claims),'article':ident(pathlib.Path(ARTICLE).name)},sort_keys=True));return
    receipt={'_license':license_('machine_readable_prepublication_return_receipt'),'schema':'qikvrt_prepublication_return_receipt_v2','publication_id':PID,'content_changed':False,'original_files':[],'candidate_files':[ident(pathlib.Path(ARTICLE).name)],'changed_claim_ids':[],'change_reasons':[],'change_notice_path':None,'return':{'candidate_returned_to_owner':True,'owner_name':'Ingolf Lohmann','owner_type':'NATURAL_PERSON','return_channel':'ChatGPT conversation: sandbox:/mnt/data/PR1128_Rueckgabe_Original_und_Quellen.zip','returned_at':args.returned_at,'visible_change_notice_returned':False}}
    put('PREPUBLICATION_RETURN_RECEIPT.json',jb(receipt))
    artnames={'CLAIM_MATRIX.json':'CLAIM_MATRIX','SOURCE_BINDINGS.json':'SOURCE','QUELLEN_UND_GELTUNGSBEREICH.md':'OTHER','verify_publication_scope.py':'BOUNDARY_TEST','BOUNDARY_TEST_REPORT.json':'BOUNDARY_TEST','PREPUBLICATION_RETURN_RECEIPT.json':'RETURN_RECEIPT','README.md':'OTHER','ZENODO_METADATA.json':'OTHER'}
    artifacts=[]
    for name,kind in artnames.items():
        i=ident(name);i.pop('bytes');i['kind']=kind;artifacts.append(i)
    bc=[]
    word={'SOURCE_BOUND':'SOURCE_ATTRIBUTED','NORMATIVE':'NORMATIVE_DECLARATION','INTERPRETATIVE':'INTERPRETATIVE_DECLARATION'}
    for c in claims:bc.append({'claim_id':c['claim_id'],'statement':c['statement'],'classification':c['classification'],'status':c['status'],'publication_wording':word[c['classification']],'scope':c['boundary'],'proof_refs':[],'evidence_refs':[],'source_refs':[DIR+'/SOURCE_BINDINGS.json#'+s for s in c['sources']]})
    bundle={'_license':license_('machine_readable_proof_bundle'),'schema':'qikvrt_zenodo_machine_proof_bundle_v2','publication_id':PID,'policy':{'id':'qikvrt-zenodo-machine-proof-before-publication-v2','path':'policy/zenodo-machine-proof-policy-v2.json','version':'2.0.0','sha256':'933d6322a1e294848c6385d1384ab0ec3862c8675ebe35ec2fc4cad3e0baec47','git_blob_sha1':'e9578d30d22f845e7df684128dcd9332641c00be'},'candidate':{'primary_document_path':ARTICLE,'files':[dict(ident(pathlib.Path(ARTICLE).name),name=pathlib.Path(ARTICLE).name,role='PRIMARY')]},'claims':bc,'artifacts':artifacts,'prepublication_return':{'content_changed':False,'candidate_returned_to_owner':True,'receipt_path':DIR+'/PREPUBLICATION_RETURN_RECEIPT.json','change_notice_path':None},'gates':{k:True for k in ['all_claims_dispositioned','all_references_resolve','candidate_frozen','formal_claims_have_kernel_receipts','open_claims_not_worded_as_facts','proof_bundle_in_upload_fileset','returned_bytes_equal_upload_bytes']},'completion_claims':{'machine_proof_complete':True,'zenodo_upload_authorized':True}}
    put('MACHINE_PROOF_BUNDLE.json',jb(bundle))
    sys.path.insert(0,str(root));from tools import qikvrt_zenodo_machine_proof as proof;from tools import qikvrt_zenodo_actions as transport
    upload=[ARTICLE]+[DIR+'/'+n for n in artnames]+[DIR+'/MACHINE_PROOF_BUNDLE.json']
    checked=proof.validate_bundle(root,d/'MACHINE_PROOF_BUNDLE.json',upload_paths=upload)
    statement='AUTHORIZE_EXACT_UPLOAD authorization_id=pr1128-truth-20260919-v1 publication_id='+PID+' return_sha256='+ident('PREPUBLICATION_RETURN_RECEIPT.json')['sha256']+' metadata_sha256='+sha(transport._json_bytes(metadata))+' machine_proof_sha256='+checked['sha256']
    put('AUTHORIZE_EXACT_UPLOAD.txt','# PENDING: exact statement for a subsequent natural-person decision; not yet granted.\n'+statement+'\n')
    control={'schema':'qikvrt_pr1128_publication_control_pending_v1','publication_id':PID,'machine_proof_gate_validated':True,'machine_proof_gate_term_boundary':'The schema-fixed zenodo_upload_authorized is only the machine-proof gate. Independent natural-person authorization remains absent.','owner_exact_upload_authorized':False,'owner_authorization_record_present':False,'native_P3':False,'P4':False,'Main_promotion':False,'zenodo_record_state':'UNVERIFIED','zenodo_readback':'REQUIRED_AFTER_AUTHORIZED_PUBLICATION','PREDECESSOR_EVIDENCE_TRANSFER':False,'production_mutations':0,'DONE':False,'EFFECT_ACK_DONE':False,'intended_upload_paths':upload,'required_statement':statement,'proof_identity':checked,'candidate_return_identity':ident('PREPUBLICATION_RETURN_RECEIPT.json'),'canonical_metadata_sha256':sha(transport._json_bytes(metadata)),'controls_excluded_from_upload':['AUTHORIZE_EXACT_UPLOAD.txt','PUBLICATION_CONTROL_PENDING.json']}
    put('PUBLICATION_CONTROL_PENDING.json',jb(control))
    print(json.dumps({'stage':'MACHINE_PROOF_GATE_VERIFIED_OWNER_AUTHORIZATION_PENDING','claims':len(claims),'statement':statement,'article_unchanged':True},sort_keys=True))
if __name__=='__main__':main()
