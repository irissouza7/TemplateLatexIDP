from __future__ import annotations
import csv, re, time
from pathlib import Path
from urllib.parse import quote
import requests

PROXY = 'http://siprx.caixa:9090'
PROXIES = {'http': PROXY, 'https': PROXY}
OUT = Path('referencias_pdf')
OUT.mkdir(exist_ok=True)

DOIS = [
'10.3390/buildings16030485','10.1108/ci-08-2023-0182','10.1371/journal.pone.0333189','10.48550/arXiv.2403.07815','10.1080/01621459.2021.1891924','10.1080/01446198500000015','10.1007/bf00117832','10.1007/s10208-009-9045-5','10.1609/aaai.v37i6.25854','10.1061/jcemd4.coeng-13101','10.1007/s42107-023-00980-z','10.1016/j.ijforecast.2012.09.002','10.1080/07350015.1995.10524599','10.1111/mice.13114','10.1016/j.eswa.2023.119619','10.48550/arXiv.2406.12747','10.1016/j.aej.2019.05.002','10.1155/2014/107926','10.1061/(asce)co.1943-7862.0001678','10.1080/01446190210151050','10.1214/aos/1013203451','10.48550/arXiv.2106.00170','10.48550/arXiv.2207.08815','10.1016/j.ijproman.2004.04.002','10.48550/arXiv.1604.06737','10.3982/ecta5771','10.1061/(asce)0733-9364(1998)124:3(210)','10.1162/neco.1997.9.8.1735','10.1007/978-3-540-71918-2','10.1016/j.ifacol.2022.10.127','10.1080/15623599.2025.2558070','10.3389/fdata.2021.693674','10.3390/buildings14082423','10.1016/j.buildenv.2004.02.013','10.1080/09511920210143372','10.1080/01621459.2017.1307116','10.1002/9781119482260','10.3390/buildings14103156','10.48550/arXiv.2512.09360','10.1016/j.ijforecast.2021.11.013','10.1016/j.ijforecast.2021.03.004','10.1061/jcemd4.coeng-15598','10.38094/jastt203105','10.3390/app12199729','10.1093/biomet/63.3.581','10.1080/13467581.2026.2641274','10.1080/09613218.2023.2196388','10.1061/(asce)co.1943-7862.0000689','10.3390/modelling6020035','10.1016/j.jobe.2022.104102','10.1139/l04-029','10.1093/bioinformatics/btr597','10.1016/j.trb.2017.04.013','10.1016/s0169-2070(00)00065-0','10.1007/s42452-020-03497-1','10.1007/s00521-019-04443-y','10.1061/(asce)0733-9364(2003)129:2(198)','10.1038/s41598-022-19728-x','10.1007/b106715','10.1108/ecam-05-2024-0595','10.1080/01621459.2018.1448825','10.1016/s0925-2312(01)00702-0','10.1080/13467581.2023.2294871'
]

DIRECT_PDFS = {
    'CAIXA_SINAPI_Metodologias_Conceitos.pdf': 'https://www.caixa.gov.br/Downloads/sinapi-metodologia/Livro_SINAPI_Metodologias_Conceitos.pdf',
}

HTML_REFS = {
    'Decreto_7983_2013': 'https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/decreto/d7983.htm',
    'Lei_14133_2021': 'https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm',
    'BLS_CPI_Calculation': 'https://www.bls.gov/opub/hom/cpi/calculation.htm',
}

s = requests.Session()
s.proxies.update(PROXIES)
s.headers.update({'User-Agent': 'Mozilla/5.0 reference-downloader/1.0'})


def safe_name(text: str) -> str:
    text = re.sub(r'[^A-Za-z0-9._-]+', '_', text)
    return text.strip('_')[:150]


def is_pdf(r: requests.Response) -> bool:
    ct = (r.headers.get('content-type') or '').lower()
    return 'application/pdf' in ct or r.content[:4] == b'%PDF'


def download(url: str, path: Path) -> tuple[bool, str]:
    try:
        r = s.get(url, timeout=60, allow_redirects=True)
        if r.status_code == 200 and is_pdf(r):
            path.write_bytes(r.content)
            return True, r.url
        return False, f'HTTP {r.status_code}; content-type={r.headers.get("content-type", "")}; final={r.url}'
    except Exception as e:
        return False, repr(e)


def openalex_pdf(doi: str) -> str | None:
    url = 'https://api.openalex.org/works/https://doi.org/' + quote(doi, safe='')
    try:
        r = s.get(url, timeout=30)
        if r.status_code != 200:
            return None
        data = r.json()
        candidates = []
        for key in ('best_oa_location', 'primary_location'):
            loc = data.get(key) or {}
            if loc.get('pdf_url'):
                candidates.append(loc['pdf_url'])
        for loc in data.get('locations') or []:
            if loc and loc.get('pdf_url'):
                candidates.append(loc['pdf_url'])
        return next((x for x in candidates if x), None)
    except Exception:
        return None


def special_pdf(doi: str) -> str | None:
    low = doi.lower()
    if low.startswith('10.48550/arxiv.'):
        aid = doi.split('arXiv.', 1)[-1]
        return f'https://arxiv.org/pdf/{aid}.pdf'
    if low.startswith('10.1371/journal.pone.'):
        return f'https://journals.plos.org/plosone/article/file?id={doi}&type=printable'
    return None

rows = []

for i, doi in enumerate(DOIS, start=1):
    fname = f'{i:02d}_{safe_name(doi)}.pdf'
    path = OUT / fname
    print(f'[{i}/{len(DOIS)}] {doi}')
    urls = []
    sp = special_pdf(doi)
    if sp: urls.append(('especial', sp))
    oa = openalex_pdf(doi)
    if oa: urls.append(('OpenAlex/OA', oa))
    urls.append(('DOI', 'https://doi.org/' + doi))

    ok = False
    details = ''
    for source, url in urls:
        ok, details = download(url, path)
        if ok:
            rows.append([doi, 'BAIXADO', source, details, str(path)])
            print('  OK ->', path)
            break
    if not ok:
        rows.append([doi, 'NAO_BAIXADO', '', details, ''])
        print('  indisponivel automaticamente')
    time.sleep(0.2)

for name, url in DIRECT_PDFS.items():
    path = OUT / safe_name(name)
    if path.suffix.lower() != '.pdf': path = path.with_suffix('.pdf')
    ok, details = download(url, path)
    rows.append([name, 'BAIXADO' if ok else 'NAO_BAIXADO', 'link direto informado', details, str(path) if ok else ''])

with open(OUT / 'relatorio_downloads.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['referencia', 'status', 'fonte', 'url_ou_erro', 'arquivo'])
    w.writerows(rows)

with open(OUT / 'paginas_sem_pdf.txt', 'w', encoding='utf-8') as f:
    f.write('Estas referencias foram informadas como paginas HTML, nao como PDFs.\n')
    f.write('Abra no navegador e use Imprimir > Salvar como PDF, se precisar arquiva-las em PDF.\n\n')
    for name, url in HTML_REFS.items():
        f.write(f'{name}: {url}\n')

print('\nConcluido.')
print('Pasta:', OUT.resolve())
print('Relatorio:', (OUT / 'relatorio_downloads.csv').resolve())
