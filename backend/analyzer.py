import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pdfplumber

# Each category has:
#   "brands"   → brand/marque names  → 5 pts each
#   "strong"   → highly specific kw  → 3 pts each
#   "keywords" → general keywords    → 1 pt  each
CATEGORIES: dict[str, dict] = {
    "Électronique & Informatique": {
        "brands": [
            "apple", "samsung", "sony", "lg", "philips", "logitech", "razer", "corsair",
            "asus", "acer", "lenovo", "dell", "hp", "msi", "gigabyte", "anker", "belkin",
            "jabra", "bose", "jbl", "sennheiser", "beats", "hyperx", "steelseries",
            "seagate", "western digital", "sandisk", "kingston", "crucial",
            "tp-link", "netgear", "linksys", "ubiquiti", "synology",
            "nvidia", "intel", "amd", "noctua", "be quiet", "cooler master",
            "elgato", "wacom", "brother", "canon", "epson", "dymo",
        ],
        "strong": [
            "iphone", "ipad", "macbook", "airpods", "apple watch", "mac mini",
            "galaxy", "pixel", "oneplus", "xiaomi", "oppo", "realme",
            "playstation", "ps4", "ps5", "xbox", "nintendo switch", "steam deck",
            "raspberry pi", "arduino", "esp32", "microcontrôleur",
            "ssd", "nvme", "carte mère", "carte graphique", "cpu", "gpu",
            "processeur", "ventirad", "watercooling",
        ],
        "keywords": [
            "laptop", "ordinateur", "pc portable", "tour pc", "mini pc",
            "tablette", "clavier", "souris", "trackpad", "écran", "moniteur",
            "casque", "écouteur", "enceinte", "barre de son", "subwoofer",
            "câble", "chargeur", "adaptateur", "hub", "dock", "usb", "hdmi",
            "displayport", "thunderbolt", "prise", "multiprise",
            "batterie externe", "powerbank", "chargeur sans fil",
            "disque dur", "ram", "mémoire", "stockage",
            "imprimante", "scanner", "encre", "cartouche", "toner",
            "webcam", "microphone", "micro", "caméra", "projecteur",
            "routeur", "switch réseau", "répéteur", "wifi", "ethernet",
            "nas", "serveur", "raspberry", "arduino", "led", "strip led",
            "smartwatch", "montre connectée", "bracelet connecté",
            "gopro", "drone", "appareil photo", "objectif", "trépied",
            "gaming", "manette", "joystick", "volant", "simulation",
            "coque", "protection écran", "verre trempé", "film protecteur",
        ],
    },
    "Livres & Médias": {
        "brands": [
            "gallimard", "hachette", "flammarion", "larousse", "robert laffont",
            "albin michel", "fayard", "seuil", "actes sud", "pocket",
        ],
        "strong": [
            "roman", "manga", "bande dessinée", "bd", "comics", "light novel",
            "blu-ray", "blu ray", "4k uhd",
            "vinyl", "vinyle", "33 tours", "45 tours",
            "kindle", "ebook", "liseuse",
        ],
        "keywords": [
            "livre", "book", "biographie", "autobiographie", "essai", "guide",
            "manuel", "tutoriel", "encyclopédie", "dictionnaire", "atlas",
            "thriller", "policier", "science-fiction", "fantasy", "horreur",
            "dvd", "série", "film", "coffret", "intégrale",
            "cd", "album", "compilation", "bande originale",
            "magazine", "revue", "journal", "presse", "partitions",
        ],
    },
    "Vêtements & Mode": {
        "brands": [
            "nike", "adidas", "puma", "reebok", "under armour", "new balance", "asics",
            "levi", "tommy hilfiger", "calvin klein", "ralph lauren", "lacoste",
            "north face", "columbia", "patagonia", "arc'teryx", "salomon",
            "timberland", "ugg", "birkenstock", "converse", "vans",
        ],
        "strong": [
            "t-shirt", "tshirt", "chemise", "polo", "hoodie", "sweat-shirt",
            "pantalon", "jean", "chino", "legging", "jogging",
            "robe", "jupe", "combinaison",
            "sneaker", "basket", "running shoe", "chaussure de sport",
            "soutien-gorge", "boxer", "slip", "culotte",
        ],
        "keywords": [
            "pull", "sweat", "veste", "blouson", "manteau", "parka", "doudoune",
            "imperméable", "coupe-vent", "short", "bermuda",
            "pyjama", "nuisette", "sous-vêtement", "collant", "chaussette",
            "chaussure", "botte", "sandales", "mocassin", "espadrille",
            "sac à main", "portefeuille", "ceinture", "cravate",
            "écharpe", "bonnet", "casquette", "chapeau", "gant",
            "lunettes", "montre", "bijou", "bague", "collier", "bracelet",
            "valise", "bagage", "sac de voyage",
        ],
    },
    "Maison & Cuisine": {
        "brands": [
            "tefal", "seb", "moulinex", "delonghi", "nespresso", "dolce gusto",
            "dyson", "roomba", "irobot", "karcher", "rowenta", "calor",
            "bosch", "siemens", "whirlpool", "samsung", "lg", "miele",
            "ikea", "atmosphera", "maisons du monde",
        ],
        "strong": [
            "cafetière", "machine à café", "nespresso", "capsule", "dosette",
            "robot culinaire", "thermomix", "airfryer", "friteuse sans huile",
            "aspirateur robot", "roomba", "balai électrique", "aspirateur",
            "canapé", "lit", "matelas", "sommier", "tête de lit",
            "réfrigérateur", "lave-vaisselle", "lave-linge", "sèche-linge",
        ],
        "keywords": [
            "casserole", "poêle", "wok", "cocotte", "autocuiseur", "faitout",
            "couteau", "planche à découper", "fouet", "spatule", "louche",
            "assiette", "bol", "tasse", "verre", "carafe", "saladier",
            "bouilloire", "grille-pain", "toaster", "gaufrier", "croque",
            "mixeur", "blender", "centrifugeuse", "extracteur",
            "four", "micro-ondes", "induction", "plancha", "barbecue",
            "coussin", "plaid", "couverture", "couette", "oreiller",
            "drap", "housse de couette", "protège-matelas",
            "rideau", "store", "tapis", "moquette",
            "lampe", "luminaire", "ampoule", "lustre", "applique",
            "étagère", "bibliothèque", "meuble", "table", "chaise", "bureau",
            "cadre", "miroir", "vase", "bougie", "décoration",
            "poubelle", "rangement", "boite", "tiroir", "penderie",
            "nettoyage", "lessive", "produit ménager", "éponge",
        ],
    },
    "Sport & Loisirs": {
        "brands": [
            "decathlon", "domyos", "kalenji", "quechua", "forclaz", "artengo",
            "shimano", "garmin", "polar", "suunto", "fitbit",
            "wilson", "babolat", "head",
        ],
        "strong": [
            "vélo", "vtt", "vélo électrique", "trottinette électrique",
            "tapis de course", "vélo elliptique", "rameur", "banc de musculation",
            "sac de couchage", "tente", "hamac de camping",
            "ski", "snowboard", "surf", "kitesurf", "wingfoil",
        ],
        "keywords": [
            "running", "trail", "marathon", "course à pied",
            "yoga", "pilates", "tapis de yoga", "bloc yoga",
            "musculation", "haltère", "kettlebell", "barre de traction",
            "élastique", "bande de résistance", "corde à sauter",
            "natation", "maillot bain", "lunettes natation", "palme",
            "football", "ballon", "protège-tibia",
            "tennis", "raquette", "padel",
            "randonnée", "trekking", "bâton", "gourde",
            "camping", "bivouac", "sac à dos rando",
            "fitness", "gym", "sport",
            "escalade", "chausson escalade",
            "boxe", "arts martiaux",
        ],
    },
    "Santé & Beauté": {
        "brands": [
            "oral-b", "colgate", "sensodyne", "elmex", "signal",
            "loreal", "garnier", "nivea", "neutrogena", "la roche-posay",
            "vichy", "avene", "bioderma", "caudalie", "nuxe", "clarins",
            "gillette", "wilkinson", "braun", "remington", "philips",
            "biafine", "bepanthen", "weleda",
        ],
        "strong": [
            "sérum", "crème hydratante", "fond de teint", "mascara",
            "rouge à lèvres", "palette maquillage", "bb cream", "cc cream",
            "dentifrice", "brosse à dents électrique", "fil dentaire",
            "rasoir électrique", "épilateur", "tondeuse corps",
            "thermomètre", "tensiomètre", "oxymètre", "glucomètre",
        ],
        "keywords": [
            "shampooing", "shampoo", "après-shampooing", "masque cheveux",
            "crème", "lotion", "tonique", "huile", "baume",
            "maquillage", "cosmétique", "parfum", "eau de toilette",
            "déodorant", "anti-transpirant",
            "gel douche", "savon", "mousse lavante",
            "rasoir", "lame", "mousse à raser", "gel rasage",
            "bain de bouche", "blanchiment dents",
            "vitamines", "complément", "oméga", "magnésium", "probiotique",
            "médicament", "doliprane", "paracétamol", "ibuprofène",
            "bandage", "pansement", "désinfectant", "cicatrisant",
            "coton", "coton-tige", "lingette", "démaquillant",
        ],
    },
    "Alimentation & Épicerie": {
        "brands": [
            "nespresso", "dolce gusto", "illy", "lavazza", "carte noire",
            "lindt", "ferrero", "kinder", "haribo", "milka", "côte d'or",
            "bjorg", "bio", "jardin bio", "gerblé",
        ],
        "strong": [
            "capsule café", "dosette café", "grain de café", "café moulu",
            "protéine whey", "créatine", "bcaa", "barre protéinée",
            "complément sportif", "boisson isotonique",
        ],
        "keywords": [
            "café", "thé", "infusion", "tisane", "matcha", "kombucha",
            "chocolat", "bonbon", "confiserie", "biscuit", "gâteau", "cookie",
            "snack", "chips", "popcorn", "noix", "fruit sec", "muesli", "céréale",
            "pâte", "riz", "semoule", "farine", "sucre", "sel", "épice",
            "huile", "vinaigre", "sauce", "moutarde", "mayonnaise",
            "eau", "soda", "jus", "sirop", "limonade",
            "vin", "bière", "whisky", "rhum", "gin", "cidre",
            "alimentaire", "nourriture", "épicerie",
        ],
    },
    "Jeux & Jouets": {
        "brands": [
            "lego", "playmobil", "hasbro", "mattel", "ravensburger", "clementoni",
            "fisher-price", "vtech", "leapfrog", "chicco", "brio", "haba",
        ],
        "strong": [
            "lego technic", "lego city", "lego star wars", "lego ninjago",
            "playmobil city", "playmobil pirates",
            "jeu de société", "jeu de plateau", "jeu de cartes",
            "peluche", "doudou",
        ],
        "keywords": [
            "figurine", "poupée", "puzzle", "kapla", "duplo", "mécano",
            "construction jouet", "voiture télécommandée", "drone jouet",
            "jeu éducatif", "balle jouet", "trottinette enfant", "vélo enfant",
            "dessin", "coloriage", "pâte à modeler",
            "déguisement", "costume enfant",
        ],
    },
    "Fournitures & Bureau": {
        "brands": [
            "bic", "pilot", "stabilo", "staedtler", "moleskine", "leuchtturm",
            "avery", "scotch", "pritt", "veleda",
        ],
        "strong": [
            "stylo à bille", "stylo plume", "stylo gel",
            "cahier spirale", "carnet moleskine",
            "post-it", "note adhésive",
            "agrafeuse", "destructeur de documents", "plastifieuse",
            "fauteuil ergonomique", "chaise de bureau",
        ],
        "keywords": [
            "stylo", "crayon", "feutre", "surligneur", "marqueur",
            "cahier", "carnet", "bloc-notes", "agenda",
            "classeur", "chemise", "pochette", "porte-documents",
            "reliure", "papier", "rame", "enveloppe", "étiquette",
            "scotch adhésif", "colle", "ciseaux", "taille-crayon",
            "calculatrice", "règle", "équerre",
            "bureau", "organiseur bureau",
        ],
    },
    "Jardin & Bricolage": {
        "brands": [
            "bosch", "makita", "dewalt", "stanley", "black decker", "ryobi",
            "karcher", "husqvarna", "stihl", "gardena", "hozelock",
        ],
        "strong": [
            "perceuse visseuse", "scie circulaire", "ponceuse orbitale",
            "taille-haie", "débroussailleuse", "tondeuse gazon",
            "nettoyeur haute pression",
        ],
        "keywords": [
            "perceuse", "visseuse", "marteau", "tournevis", "pince", "scie",
            "ponceuse", "meuleuse", "niveau", "mètre ruban",
            "vis", "cheville", "boulon", "clou", "écrou",
            "peinture", "rouleau peinture", "pinceau", "enduit", "vernis",
            "colle", "mastic", "joint", "silicone",
            "tuyau", "robinet", "plomberie", "siphon",
            "plante", "pot", "terreau", "engrais", "graine", "bulbe",
            "arrosoir", "tuyau arrosage", "asperseur",
            "jardin", "potager", "compost",
            "barbecue", "parasol", "salon de jardin", "transat",
        ],
    },
    "Auto & Moto": {
        "brands": [
            "michelin", "continental", "bridgestone", "pirelli", "goodyear",
            "bosch auto", "valeo", "midas",
        ],
        "strong": [
            "pneu auto", "jante aluminium", "chaîne neige",
            "dashcam", "radar de recul", "caméra 360",
            "siège auto bébé", "rehausseur enfant",
        ],
        "keywords": [
            "pneu", "jante", "roue", "enjoliveur",
            "huile moteur", "filtre à huile", "filtre air", "filtre habitacle",
            "batterie voiture", "essuie-glace", "ampoule voiture",
            "plaquette frein", "disque frein", "liquide frein",
            "autoradio", "gps voiture", "câble recharge voiture",
            "tapis voiture", "housses siège", "couvre-volant",
            "casque moto", "gant moto", "gilet réfléchissant",
            "véhicule", "automobile",
        ],
    },
    "Animaux": {
        "brands": [
            "royal canin", "purina", "hills", "pedigree", "whiskas",
            "kong", "trixie", "ferplast", "catit",
        ],
        "strong": [
            "croquette chien", "croquette chat", "pâtée chien", "pâtée chat",
            "litière agglomérante", "bac à litière",
            "arbre à chat", "griffoir",
        ],
        "keywords": [
            "croquette", "pâtée animaux", "nourriture chien", "nourriture chat",
            "laisse", "collier chien", "harnais", "muselière",
            "cage transport", "panier animal",
            "jouet chien", "jouet chat", "friandise animaux",
            "aquarium", "nourriture poisson",
            "rongeur", "hamster", "lapin", "oiseau",
            "antiparasitaire", "vermifuge", "shampooing animal",
        ],
    },
    "Bébé & Puériculture": {
        "brands": [
            "pampers", "huggies", "chicco", "babybjorn", "cybex", "maxi-cosi",
            "ingenuity", "nuby", "tommee tippee", "philips avent",
        ],
        "strong": [
            "couche bébé", "couche-culotte", "lait infantile", "lait maternisé",
            "poussette", "nacelle", "siège auto bébé", "cosy",
        ],
        "keywords": [
            "bébé", "nourrisson", "biberon", "tétine", "sucette",
            "parc bébé", "transat bébé", "relax bébé",
            "vêtement bébé", "body bébé", "pyjama bébé",
            "jouet éveil", "tapis éveil", "mobile bébé",
            "baignoire bébé", "siège de bain",
        ],
    },
}

MONTH_NAMES_FR = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]


def _clean_html(raw: str) -> str:
    """Strip HTML tags and decode common entities."""
    text = re.sub(r'<[^>]+>', ' ', raw)
    for ent, ch in [('&amp;', '&'), ('&quot;', '"'), ('&#39;', "'"),
                    ('&lt;', '<'), ('&gt;', '>'), ('&nbsp;', ' ')]:
        text = text.replace(ent, ch)
    return ' '.join(text.split())


def categorize_item(item_name: str) -> str:
    if not item_name or not item_name.strip():
        return "Autres"
    name_lower = item_name.lower()

    best_cat, best_score = "Autres", 0

    for cat, data in CATEGORIES.items():
        score = 0
        # Brands  → 5 pts (high signal)
        for brand in data.get("brands", []):
            if brand in name_lower:
                score += 5
        # Strong keywords → 3 pts
        for kw in data.get("strong", []):
            if kw in name_lower:
                score += 3
        # Generic keywords → 1 pt
        for kw in data.get("keywords", []):
            if kw in name_lower:
                score += 1

        if score > best_score:
            best_score = score
            best_cat = cat

    return best_cat


def _extract_largest_amount(text: str) -> float:
    amounts = re.findall(r'(\d[\d\s]*[,\.]\d{2})\s*(?:€|EUR)', text)
    values = []
    for a in amounts:
        try:
            values.append(float(a.replace(' ', '').replace(',', '.')))
        except ValueError:
            pass
    return max(values) if values else 0.0


def parse_invoice_pdf(pdf_path: str) -> dict:
    result = {
        "filename": os.path.basename(pdf_path),
        "order_id": None,
        "date": None,
        "total": 0.0,
        "items": [],
        "category": "Autres",
    }

    fname = os.path.basename(pdf_path)

    # Order ID from filename
    m = re.search(r'(\d{3}-\d{7}-\d{7})', fname)
    if m:
        result["order_id"] = m.group(1)

    # Date from filename
    m = re.search(r'(\d{4}-\d{2}-\d{2})', fname)
    if m:
        result["date"] = m.group(1)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(
                (p.extract_text() or "") for p in pdf.pages
            )

        # Order ID from text
        if not result["order_id"]:
            m = re.search(r'(\d{3}-\d{7}-\d{7})', full_text)
            if m:
                result["order_id"] = m.group(1)

        # Date from text (French)
        if not result["date"]:
            m = re.search(
                r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|'
                r'août|septembre|octobre|novembre|décembre)\s+(\d{4})',
                full_text, re.IGNORECASE)
            if m:
                month_names_lower = [n.lower() for n in MONTH_NAMES_FR]
                day, mname, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
                month = month_names_lower.index(mname) + 1
                result["date"] = f"{year:04d}-{month:02d}-{day:02d}"

        # Total – try keyword patterns first
        total_patterns = [
            r'Total\s+de\s+la\s+commande\s*:?\s*([\d\s]+[,\.]\d{2})\s*€',
            r'Grand\s+[Tt]otal\s*:?\s*(?:\$|€|EUR)?\s*([\d\s]+[,\.]\d{2})',
            r'Total\s+TTC\s*:?\s*([\d\s]+[,\.]\d{2})\s*€',
            r'Montant\s+total\s*:?\s*([\d\s]+[,\.]\d{2})\s*€',
            r'Order\s+[Tt]otal\s*:?\s*(?:\$|€)?\s*([\d\s]+[,\.]\d{2})',
            r'Commande\s+Total\s*:?\s*(?:\$|€)?\s*([\d\s]+[,\.]\d{2})',
        ]
        for pat in total_patterns:
            m = re.search(pat, full_text, re.IGNORECASE)
            if m:
                try:
                    result["total"] = float(
                        m.group(1).replace(' ', '').replace(',', '.'))
                    break
                except ValueError:
                    pass

        if result["total"] == 0.0:
            result["total"] = _extract_largest_amount(full_text)

        # Items (best-effort line parsing)
        items = []
        in_section = False
        for line in full_text.splitlines():
            line = line.strip()
            if re.search(r'(description|produit|article|désignation|item)', line, re.I):
                in_section = True
                continue
            if re.search(r'(sous-total|sous total|subtotal|total\s)', line, re.I):
                in_section = False
            if in_section and line:
                pm = re.search(r'([\d,\.]+)\s*€', line)
                if pm:
                    try:
                        price = float(pm.group(1).replace(',', '.'))
                    except ValueError:
                        price = 0.0
                    name = re.sub(r'[\d,\.]+ ?€', '', line).strip()
                    name = re.sub(r'\s{2,}', ' ', name)
                    if len(name) > 3 and 0 < price < 5000:
                        items.append({"name": name[:120], "price": price})

        result["items"] = items

        if items:
            cat_scores: dict = defaultdict(float)
            for it in items:
                cat_scores[categorize_item(it["name"])] += it["price"]
            result["category"] = max(cat_scores, key=cat_scores.get)
        elif result["order_id"]:
            # Try to infer from order ID context (fallback)
            result["category"] = "Autres"

    except Exception as exc:
        result["error"] = str(exc)

    return result


class InvoiceAnalyzer:
    def analyze_orders(self, orders: list) -> dict:
        """Analyze orders scraped directly from Amazon (no PDFs needed).
        Re-runs categorisation here so updated keywords always apply."""
        invoices = []
        for o in orders:
            items_raw = o.get("items", [])
            # Re-categorise using the latest keyword lists
            if items_raw:
                from collections import Counter
                cats = Counter(categorize_item(name) for name in items_raw)
                category = cats.most_common(1)[0][0]
            else:
                category = o.get("category", "Autres")
            invoices.append({
                "order_id": o.get("id"),
                "date":     o.get("date"),
                "total":    float(o.get("total", 0) or 0),
                "category": category,
                "items":    items_raw,
            })
        return self._aggregate(invoices)

    def analyze(self, download_path: str) -> dict:
        pdf_dir = Path(download_path)
        if not pdf_dir.exists():
            return {"error": "Le dossier spécifié n'existe pas."}

        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            return {"error": "Aucun fichier PDF trouvé dans ce dossier."}

        invoices = [parse_invoice_pdf(str(f)) for f in pdf_files]
        return self._aggregate(invoices)

    def _aggregate(self, invoices: list) -> dict:
        valid = [inv for inv in invoices if inv["total"] > 0]
        total_spent = sum(inv["total"] for inv in valid)

        by_category: dict = defaultdict(float)
        for inv in valid:
            by_category[inv["category"]] += inv["total"]

        by_month: dict = defaultdict(float)
        for inv in valid:
            if inv.get("date"):
                try:
                    dt = datetime.strptime(inv["date"], "%Y-%m-%d")
                    by_month[dt.strftime("%Y-%m")] += inv["total"]
                except ValueError:
                    pass

        sorted_months = sorted(by_month.items())

        cumulative, running = [], 0.0
        for month, amount in sorted_months:
            running += amount
            cumulative.append({"month": month, "total": round(running, 2)})

        return {
            "total_spent": round(total_spent, 2),
            "invoice_count": len(invoices),
            "valid_count": len(valid),
            "by_category": [
                {"name": cat, "value": round(amt, 2)}
                for cat, amt in sorted(by_category.items(),
                                        key=lambda x: x[1], reverse=True)
            ],
            "by_month": [
                {"month": m, "amount": round(a, 2)}
                for m, a in sorted_months
            ],
            "cumulative": cumulative,
            "top_invoices": sorted(
                [{
                    "id":       inv.get("order_id", "?"),
                    "date":     inv.get("date", ""),
                    "total":    inv["total"],
                    "category": inv.get("category", "Autres"),
                    "products": inv.get("items", [])[:3],
                } for inv in valid],
                key=lambda x: x["total"],
                reverse=True
            )[:10],
            "commentary": self._commentary(invoices, by_category, by_month, total_spent),
        }

    def _commentary(self, invoices, by_category, by_month, total_spent) -> list:
        insights = []
        n = len([i for i in invoices if i["total"] > 0])
        if n == 0:
            return []

        avg = total_spent / n if n else 0
        insights.append({
            "type": "total", "icon": "💰",
            "title": "Vue d'ensemble",
            "text": (
                f"Vous avez passé {n} commande(s) pour un total de "
                f"{total_spent:.2f} €. Votre panier moyen est de {avg:.2f} €."
            ),
        })

        if by_category:
            top_cat = max(by_category, key=by_category.get)
            pct = by_category[top_cat] / total_spent * 100 if total_spent else 0
            insights.append({
                "type": "category", "icon": "🏷️",
                "title": "Catégorie principale",
                "text": (
                    f'"{top_cat}" représente {by_category[top_cat]:.2f} € '
                    f"({pct:.1f}% du total) sur {len(by_category)} catégorie(s)."
                ),
            })

        if by_month:
            peak = max(by_month, key=by_month.get)
            try:
                dt = datetime.strptime(peak, "%Y-%m")
                peak_label = f"{MONTH_NAMES_FR[dt.month - 1]} {dt.year}"
                seasonal = ""
                if dt.month == 12:
                    seasonal = " (probablement lié aux fêtes de fin d'année)"
                elif dt.month in (1, 7):
                    seasonal = " (période de soldes)"
                elif dt.month == 11:
                    seasonal = " (Black Friday / Cyber Monday ?)"
            except ValueError:
                peak_label = peak
                seasonal = ""

            insights.append({
                "type": "timing", "icon": "📅",
                "title": "Mois le plus dépensier",
                "text": (
                    f"Le pic de dépenses est en {peak_label} avec "
                    f"{by_month[peak]:.2f} €{seasonal}."
                ),
            })

        if len(by_month) > 1:
            avg_monthly = total_spent / len(by_month)
            insights.append({
                "type": "rate", "icon": "📈",
                "title": "Cadence de dépense",
                "text": (
                    f"Dépense mensuelle moyenne : {avg_monthly:.2f} €. "
                    f"Extrapolé sur 12 mois : {avg_monthly * 12:.2f} €/an."
                ),
            })

        if len(by_category) >= 4:
            top3 = sum(sorted(by_category.values(), reverse=True)[:3])
            pct3 = top3 / total_spent * 100 if total_spent else 0
            insights.append({
                "type": "diversity", "icon": "🔍",
                "title": "Diversité des achats",
                "text": (
                    f"Achats répartis sur {len(by_category)} catégories. "
                    f"Le top 3 concentre {pct3:.1f}% du budget."
                ),
            })

        return insights
