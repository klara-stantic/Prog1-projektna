import csv
import json
import os
import requests
import sys
import requests_html
import re


# URL glavne strani 
frontpage = 'https://musescore.com/sheetmusic'
#https://musescore.com/sheetmusic?page=2
# mapa, v katero bomo shranili podatke
directory_music = 'music'
# ime datoteke v katero bomo shranili glavno stran
frontpage_filename = 'sheet_music_frontpage.html'
# ime datoteke s pognanim javascript delom
frontpage_fixed = "fixed_music.html"
# ime CSV datoteke v katero bomo shranili podatke
csv_filename = 'music.csv'

session = requests_html.HTMLSession()


def pripravi_imenik(dir):
    '''Če še ne obstaja, pripravi prazen imenik za dano datoteko.'''
    imenik = os.path.dirname(dir)
    if imenik:
        os.makedirs(imenik, exist_ok=True)

def shrani_spletno_stran(url, ime_datoteke, dir, vsili_prenos=False):
    '''Vsebino strani na danem naslovu shrani v datoteko z danim imenom.'''
    try:
        print(f'Shranjujem {url} ...', end='')
        sys.stdout.flush()
        if os.path.isfile(ime_datoteke) and not vsili_prenos:
            print('shranjeno že od prej!')
            return
        r = session.get(url)
        r.html.render()
    except requests.exceptions.ConnectionError:
        print('stran ne obstaja!')
    else:
        pripravi_imenik(dir)
        path = os.path.join(dir, ime_datoteke)
        with open(path, 'w', encoding='utf-8') as datoteka:
            datoteka.write(r.html.html)
            print('shranjeno!')

###############################################################################
# STAGE 2: Obdelava podatkov
###############################################################################


def read_file_to_string(directory, filename):
    """Funkcija vrne celotno vsebino datoteke "directory"/"filename" kot niz"""
    path = os.path.join(directory, filename)
    with open(path, 'r', encoding='utf-8') as file_in:
        return file_in.read()


blok_regular = r"<article class=\"c9ju0 J5IQp mX2qa\">(.*?)</div></article>"


def page_to_entry(page_content):
    """Funkcija niz, ki predstavlja spletno  stran, razdeli na dele, 
    ki predstavljajo posamezne vnose, in iz njih pripravi seznam"""
    rx = re.compile(blok_regular,
                    re.DOTALL)
    entries = re.findall(rx, page_content)
    return entries

blok_razrezan_reg = r"<span class=\"xBwRG .*? HtKJn\">(?P<tezavnost>.*?)</span>.*?<h2 class=\"mJ3Cr Ggd5G N30cN gHy59\">(?P<naslov>.*?)</h2>.*?<div class=\"djeI8\"><.*?>(?P<avtor>.*?)</a>.*?<div class=\"KYeND Mu94Z WJGhZ\">((?P<parts>.*?) • (?P<pages>.*?) • (?P<time>.*?) • (?P<date>.*?) • (?P<views>.*?) • (?P<favourites>.*?))</div>.*?</div><div class=\"C4LKv fLob3 J5IQp DIiWA\">(?P<zasedba>.*?)</div>.*?<div class=\"C4LKv B6vE9 DIiWA z99NF\">(?P<instrument>.*?)</div>"

public_domain_reg = r"<span class=\"xBwRG o1QE0 HtKJn cPGYN\">(.*?)</span>"

def get_dict_from_block(block):
    """Funkcija iz niza za posamezen vnos izlušči podatke, 
    ki nas o njem zanimajo, ter vrne slovar, ki vsebuje ustrezne
    podatke"""
    rx = re.compile(blok_razrezan_reg,
                    re.DOTALL)
    data = re.search(rx, block)
    blok_dict = data.groupdict()

    # Ker niso vsi vnosi v javni rabi, to rešimo z dodatnim vzorcem
    rloc = re.compile(public_domain_reg)
    locdata = re.search(rloc, block)
    if locdata is not None:
        blok_dict['javna domena'] = "DA"
    else:
        blok_dict['javna domena'] = 'NE'

    return blok_dict


def blocks_from_file(filename, directory):
    """Funkcija prebere podatke v datoteki "directory"/"filename" in jih
   pretvori (razčleni) v pripadajoč seznam slovarjev za vsak vnos posebej."""
    page = read_file_to_string(filename, directory)
    blocks = page_to_entry(page)
    bloki = [get_dict_from_block(block) for block in blocks]
    return bloki


def bloki_frontpage(directory):
    return blocks_from_file(directory, frontpage_filename)

###############################################################################
# STAGE 3: Shranjevanje podatkov 
################################################################################


def write_csv(fieldnames, rows, directory, filename):
    """
    Funkcija v csv datoteko podano s parametroma "directory"/"filename" zapiše
    vrednosti v parametru "rows" pripadajoče ključem podanim v "fieldnames"
    """
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, 'w', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return None

# Definirajte funkcijo, ki sprejme neprazen seznam slovarjev, ki predstavljajo
# podatke iz oglasa mačke, in zapiše vse podatke v csv datoteko. Imena za
# stolpce [fieldnames] pridobite iz slovarjev.


def write_bloki_to_csv(bloki, directory, filename):
    """Funkcija vse podatke iz parametra "bloki" zapiše v csv datoteko podano s
    parametroma "directory"/"filename". Funkcija predpostavi, da so ključi vseh
    slovarjev parametra bloki enaki in je seznam bloki neprazen."""
    # Stavek assert preveri da zahteva velja
    # Če drži se program normalno izvaja, drugače pa sproži napako
    # Prednost je v tem, da ga lahko pod določenimi pogoji izklopimo v
    # produkcijskem okolju
    assert bloki and (all(j.keys() == bloki[0].keys() for j in bloki))
    write_csv(bloki[0].keys(), bloki, directory, filename)


def main(redownload=True, reparse=True):
    # Vsebino spletne strani shranimo v tekstovno datoteko
    shrani_spletno_stran(frontpage, frontpage_filename, directory_music)

    # Iz lokalne (html) datoteke preberemo podatke
    bloki = page_to_entry(read_file_to_string(directory_music, frontpage_filename))

    # Podatke preberemo v lepšo obliko (seznam slovarjev)
    bloki_lepse = [get_dict_from_block(blok) for blok in bloki]

    # Podatke shranimo v csv datoteko
    write_bloki_to_csv(bloki_lepse, directory_music, csv_filename)

if __name__ == '__main__':
    main()