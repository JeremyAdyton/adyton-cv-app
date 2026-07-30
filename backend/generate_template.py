"""
generate_template.py — Génération DOCX Adyton depuis données structurées CV
"""

import copy
import io
import os
import re
import zipfile
from lxml import etree

NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'
BASE_TEMPLATE = os.path.join(os.path.dirname(__file__), 'assets', 'Template_Adyton_BASE.docx')


def W(tag):
    return f'{{{NS}}}{tag}'


def get_text(el):
    return ''.join(t.text or '' for t in el.findall(f'.//{W("t")}'))


def find_para(body, placeholder):
    for el in list(body):
        if el.tag == W('p') and placeholder in get_text(el):
            return el
    return None


def find_in_table(body, placeholder):
    for el in list(body):
        if el.tag == W('tbl'):
            for tc in el.findall(f'.//{W("tc")}'):
                if placeholder in get_text(tc):
                    return tc
    return None


def set_text(para, text):
    runs = para.findall(f'.//{W("r")}')
    if not runs:
        r = etree.SubElement(para, W('r'))
        t_el = etree.SubElement(r, W('t'))
        t_el.text = text
        t_el.set(XML_SPACE, 'preserve')
        return
    for r in runs:
        for t in r.findall(W('t')):
            t.text = ''
    t_el = runs[0].find(W('t'))
    if t_el is None:
        t_el = etree.SubElement(runs[0], W('t'))
    t_el.text = text
    t_el.set(XML_SPACE, 'preserve')


def set_cell_text(tc, text):
    paras = tc.findall(f'.//{W("p")}')
    if not paras:
        return
    for p in paras[1:]:
        tc.remove(p)
    set_text(paras[0], text)


def set_mission_header(para, company, date):
    runs = para.findall(f'.//{W("r")}')
    if not runs:
        return
    for r in runs:
        for t in r.findall(W('t')):
            t.text = ''
    t0 = runs[0].find(W('t'))
    if t0 is None:
        t0 = etree.SubElement(runs[0], W('t'))
    t0.text = company.ljust(85)
    t0.set(XML_SPACE, 'preserve')
    t_last = runs[-1].find(W('t'))
    if t_last is None:
        t_last = etree.SubElement(runs[-1], W('t'))
    t_last.text = date
    t_last.set(XML_SPACE, 'preserve')


def set_contexte(para, contexte_text):
    runs = para.findall(f'.//{W("r")}')
    for r in runs:
        for t in r.findall(W('t')):
            if '{{CONTEXTE}}' in (t.text or ''):
                t.text = contexte_text
                t.set(XML_SPACE, 'preserve')
                return
    set_text(para, f'Contexte technique/Outils : {contexte_text}')


def insert_after(anchor, new_el):
    parent = anchor.getparent()
    idx = list(parent).index(anchor)
    parent.insert(idx + 1, new_el)
    return new_el


def clone(ref, text=None):
    cl = copy.deepcopy(ref)
    if text is not None:
        set_text(cl, text)
    return cl


def generate(cv_data: dict) -> bytes:
    """Génère le DOCX et retourne les bytes du fichier."""
    with open(BASE_TEMPLATE, 'rb') as f:
        base_bytes = f.read()

    with zipfile.ZipFile(io.BytesIO(base_bytes), 'r') as zin:
        doc_xml = zin.read('word/document.xml')
        all_files = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    tree = etree.fromstring(doc_xml)
    root = tree
    body = root.find(f'.//{W("body")}')

    # ── NOM ──────────────────────────────────────────────────────────────────
    nom_p = find_para(body, '{{NOM}}')
    if nom_p is not None:
        set_text(nom_p, cv_data['nom'].upper())

    # ── TITRE ─────────────────────────────────────────────────────────────────
    titre_p = find_para(body, '{{TITRE}}')
    if titre_p is not None:
        set_text(titre_p, cv_data['titre'])

    # ── PROFIL ────────────────────────────────────────────────────────────────
    profil = (cv_data.get('profil', []) + [''] * 4)[:4]
    for i, text in enumerate(profil, 1):
        ph = find_para(body, f'{{{{PROFIL_{i}}}}}')
        if ph is not None:
            set_text(ph, text)

    # ── COMPÉTENCES ───────────────────────────────────────────────────────────
    competences = cv_data.get('competences', [])
    for i, comp in enumerate(competences[:7], 1):
        cat_tc = find_in_table(body, f'{{{{CAT_{i}}}}}')
        cnt_tc = find_in_table(body, f'{{{{CONTENU_{i}}}}}')
        if cat_tc is not None:
            set_cell_text(cat_tc, comp.get('categorie', ''))
        if cnt_tc is not None:
            set_cell_text(cnt_tc, comp.get('contenu', ''))
    for i in range(len(competences) + 1, 8):
        for ph in [f'{{{{CAT_{i}}}}}', f'{{{{CONTENU_{i}}}}}']:
            tc = find_in_table(body, ph)
            if tc is not None:
                set_cell_text(tc, '')

    # ── FORMATION ─────────────────────────────────────────────────────────────
    formation = cv_data.get('formation', [])
    form_ph = find_para(body, '{{FORMATION_1}}')
    if form_ph is not None:
        if formation:
            set_text(form_ph, formation[0])
            cursor = form_ph
            for line in formation[1:]:
                cursor = insert_after(cursor, clone(form_ph, line))
        else:
            set_text(form_ph, '')

    # ── MISSIONS ──────────────────────────────────────────────────────────────
    missions = cv_data.get('missions', [])
    company_ph = find_para(body, '{{COMPANY}}')
    role_ph    = find_para(body, '{{ROLE}}')
    bullet_ph  = find_para(body, '{{BULLET}}')
    env_ph     = find_para(body, '{{CONTEXTE}}')

    if company_ph is not None and missions:
        items = list(body)
        idx_company = items.index(company_ph)
        ref_empty   = items[idx_company - 1]
        idx_env     = items.index(env_ph)

        to_remove = items[idx_company: idx_env + 3]
        for el in to_remove:
            if el.tag != W('sectPr'):
                try:
                    body.remove(el)
                except ValueError:
                    pass

        cursor = ref_empty
        for m in missions:
            hdr = copy.deepcopy(company_ph)
            set_mission_header(hdr, m.get('company', ''), m.get('date', ''))
            cursor = insert_after(cursor, hdr)
            cursor = insert_after(cursor, clone(role_ph, m.get('role', '')))
            cursor = insert_after(cursor, clone(ref_empty))
            for b in m.get('bullets', []):
                cursor = insert_after(cursor, clone(bullet_ph, b))
            cursor = insert_after(cursor, clone(ref_empty))
            ep = copy.deepcopy(env_ph)
            set_contexte(ep, m.get('contexte', ''))
            cursor = insert_after(cursor, ep)
            cursor = insert_after(cursor, clone(ref_empty))
            cursor = insert_after(cursor, clone(ref_empty))

    # ── VALIDATION ────────────────────────────────────────────────────────────
    full_text = get_text(root)
    remaining = re.findall(r'\{\{[^}]+\}\}', full_text)
    if remaining:
        raise ValueError(f"Placeholders non remplis : {set(remaining)}")

    # ── OUTPUT ────────────────────────────────────────────────────────────────
    new_doc_xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(base_bytes), 'r') as zin:
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == 'word/document.xml':
                    zout.writestr('word/document.xml', new_doc_xml)
                else:
                    zout.writestr(item, zin.read(item.filename))

    return output.getvalue()
