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

# Position du taquet de tabulation pour l'alignement à droite des dates de mission
# = largeur utile de la page (pgW - marges L/R). pgSz w=11906, pgMar left=900 right=900.
MISSION_DATE_TAB_POS = "10106"

# Pied de page légal Adyton (trait bleu + mentions), injecté sur toutes les pages
FOOTER_TEXT = ("Adyton Consulting – 3 rue Charcot – 92 200 Neuilly sur Seine "
               "– SAS au Capital de 40 000€ - RCS de Paris 495 207 201")
BRAND_BLUE = "17457A"


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
    """Écrit société + date sur la ligne d'en-tête de mission. La date est poussée
    par un vrai taquet de tabulation aligné à droite (voir ensure_right_tab_stop),
    pas par un padding d'espaces : ça la colle exactement en bout de ligne quelle
    que soit la longueur du nom de société, même avec une police à chasse variable."""
    runs = para.findall(f'.//{W("r")}')
    if not runs:
        return
    for r in runs:
        for t in r.findall(W('t')):
            t.text = ''
    t0 = runs[0].find(W('t'))
    if t0 is None:
        t0 = etree.SubElement(runs[0], W('t'))
    t0.text = company
    t0.set(XML_SPACE, 'preserve')

    last_run = runs[-1]
    t_last = last_run.find(W('t'))
    if t_last is None:
        t_last = etree.SubElement(last_run, W('t'))
    # Insère un vrai <w:tab/> juste avant le texte de la date
    tab_el = etree.Element(W('tab'))
    last_run.insert(list(last_run).index(t_last), tab_el)
    t_last.text = date
    t_last.set(XML_SPACE, 'preserve')


def ensure_right_tab_stop(para, pos=MISSION_DATE_TAB_POS):
    """Ajoute un taquet de tabulation aligné à droite au paragraphe (une seule fois),
    pour que le <w:tab/> inséré par set_mission_header pousse la date jusqu'au bord
    droit de la page."""
    pPr = para.find(W('pPr'))
    if pPr is None:
        pPr = etree.Element(W('pPr'))
        para.insert(0, pPr)
    if pPr.find(W('tabs')) is not None:
        return
    tabs = etree.Element(W('tabs'))
    tab = etree.SubElement(tabs, W('tab'))
    tab.set(W('val'), 'right')
    tab.set(W('pos'), pos)
    # Ordre du schéma CT_PPr : w:tabs doit venir après w:pBdr s'il est présent
    pBdr = pPr.find(W('pBdr'))
    if pBdr is not None:
        pBdr.addnext(tabs)
    else:
        pPr.insert(0, tabs)


def format_display_name(nom_json: str) -> str:
    """Convertit le nom stocké au format 'NOM Prénom' (ex: 'DUPONT Thomas') en
    affichage 'Prénom NOM' (ex: 'Thomas DUPONT') : prénom en casse normale, nom de
    famille en MAJUSCULES — c'est le format validé par le client (le premier ordre,
    tout en majuscules, avait été jugé pas assez lisible)."""
    parts = nom_json.strip().split()
    if len(parts) < 2:
        return nom_json
    nom_famille, prenom = parts[0], " ".join(parts[1:])
    return f"{prenom} {nom_famille.upper()}"


def remove_empty_profil_paragraphs(body):
    """Si moins de 4 paragraphes de profil sont fournis, les entrées vides restantes
    laissent des lignes blanches avant le titre 'Compétences' : on les retire. On ne
    touche JAMAIS à l'espaceur légitime du template (paragraphe vide avec
    pStyle='Titre1' juste avant 'Compétences'), qui crée le saut de ligne normal
    entre le profil et la section suivante."""
    def has_titre1_style(el):
        pPr = el.find(W('pPr'))
        if pPr is None:
            return False
        pStyle = pPr.find(W('pStyle'))
        return pStyle is not None and pStyle.get(W('val')) == 'Titre1'

    items = list(body)
    comp_idx = None
    for i, el in enumerate(items):
        if el.tag == W('p') and get_text(el).strip() == 'Compétences':
            comp_idx = i
            break
    if comp_idx is None:
        return

    removed = 0
    j = comp_idx - 1
    while j >= 0 and removed < 3:
        el = items[j]
        if el.tag == W('p') and get_text(el).strip() == '' and not has_titre1_style(el):
            body.remove(el)
            removed += 1
            j -= 1
        else:
            break


def build_footer_xml() -> bytes:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:p>
<w:pPr>
<w:pBdr><w:top w:val="single" w:sz="6" w:space="4" w:color="{BRAND_BLUE}"/></w:pBdr>
<w:jc w:val="center"/>
<w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:color w:val="595959"/><w:sz w:val="14"/><w:szCs w:val="14"/></w:rPr>
</w:pPr>
<w:r>
<w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:color w:val="595959"/><w:sz w:val="14"/><w:szCs w:val="14"/></w:rPr>
<w:t xml:space="preserve">{FOOTER_TEXT}</w:t>
</w:r>
</w:p>
</w:ftr>'''.encode('utf-8')


def add_footer_to_parts(content_types: str, doc_rels: str, document_xml: str):
    """Ajoute la relation footer1.xml, son content-type, et le footerReference dans
    sectPr. Retourne (content_types, doc_rels, document_xml) mis à jour."""
    if 'footerReference' in document_xml:
        return content_types, doc_rels, document_xml

    rids = [int(m) for m in re.findall(r'Id="rId(\d+)"', doc_rels)]
    next_rid = max(rids) + 1 if rids else 1
    rid = f'rId{next_rid}'

    rel_tag = (f'<Relationship Id="{rid}" '
               f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" '
               f'Target="footer1.xml"/>')
    doc_rels = doc_rels.replace('</Relationships>', rel_tag + '</Relationships>')

    ct_tag = ('<Override PartName="/word/footer1.xml" '
              'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>')
    content_types = content_types.replace('</Types>', ct_tag + '</Types>')

    footer_ref = f'<w:footerReference w:type="default" r:id="{rid}"/>'

    def inject(match):
        return f'{match.group(1)}{footer_ref}{match.group(2)}</w:sectPr>'

    document_xml, _ = re.subn(r'(<w:sectPr[^>]*>)(.*?)</w:sectPr>', inject, document_xml, flags=re.S)

    return content_types, doc_rels, document_xml


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
        set_text(nom_p, format_display_name(cv_data['nom']))

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
    remove_empty_profil_paragraphs(body)

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
        ensure_right_tab_stop(company_ph)
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

    # ── OUTPUT (+ pied de page Adyton sur toutes les pages) ──────────────────
    new_doc_xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    content_types = all_files['[Content_Types].xml'].decode('utf-8')
    doc_rels = all_files['word/_rels/document.xml.rels'].decode('utf-8')
    doc_xml_str = new_doc_xml.decode('utf-8')

    content_types, doc_rels, doc_xml_str = add_footer_to_parts(content_types, doc_rels, doc_xml_str)

    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(base_bytes), 'r') as zin:
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == 'word/document.xml':
                    zout.writestr('word/document.xml', doc_xml_str.encode('utf-8'))
                elif item.filename == '[Content_Types].xml':
                    zout.writestr(item, content_types)
                elif item.filename == 'word/_rels/document.xml.rels':
                    zout.writestr(item, doc_rels)
                else:
                    zout.writestr(item, zin.read(item.filename))
            zout.writestr('word/footer1.xml', build_footer_xml())

    return output.getvalue()
