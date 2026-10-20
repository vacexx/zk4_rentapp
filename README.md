# ZK4 Rent App

Webová aplikace pro správu akcí, techniky, odpracovaného času a fakturaci společnosti ZK4 Production. Postavená na Django.

## Front-end

Vlastní tmavý design bez Bootstrapu a bez JavaScriptových závislostí. Sdílené Django šablony používají lokální SVG ikony, CSS Grid a Flexbox. Instalace Node.js ani sestavení front-endu nejsou potřeba.

- `app/static/app/workspace.css` — barvy, typografie, komponenty a responzivní rozložení.
- `app/static/app/workspace.js` — mobilní navigace, přepínání kalendáře a seznamu, týdny a dynamická pole formulářů.
- `app/static/app/invoice.css` — tiskové doklady a jejich ovládání.
- `app/templates/components/` — společné formulářové prvky a stavy akcí.
- `app/templatetags/ui.py` — SVG ikony a odkazy zachovávající filtry.

Kalendář má měsíční zobrazení a na úzkých telefonech přepínání týdnů. Vyhledávání pracuje s názvem akce i klienta, respektuje uživatele a kombinuje se s filtry. Přepnutí zobrazení zůstává v URL. Souhrnné karty zobrazují všechny akce uživatele; kalendář, seznam a nejbližší akce respektují vybrané filtry.

Typografie volitelně načítá DM Sans a Manrope z Google Fonts; bez připojení použije systémová písma. Tiskové doklady zůstávají světlé kvůli tisku.

## Lokální spuštění

V prostředí s nainstalovaným Django:

```sh
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py runserver 127.0.0.1:8000
```

Otevřete `http://127.0.0.1:8000/` a přihlaste se. V produkčním prostředí publikujte statické soubory pomocí `python3 manage.py collectstatic` a obvyklého nastavení hostingu Django.

## Ověření

```sh
python3 manage.py check
python3 manage.py test
```

Testy pokrývají fakturaci, vykreslení pracovních stránek, soukromí vyhledávání, filtry a validaci formulářů. Vizuální kontrola v prohlížeči nebyla v prostředí redesignu dokončena, protože headless prohlížeč nedokončil spuštění.
