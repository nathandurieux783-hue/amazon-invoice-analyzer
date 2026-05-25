import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pdfplumber

CATEGORIES = {
    "Électronique & Informatique": [
        "phone", "téléphone", "laptop", "ordinateur", "tablet", "tablette",
        "câble", "casque", "écouteur", "chargeur", "clé usb", "disque dur",
        "clavier", "souris", "écran", "moniteur", "imprimante", "cartouche",
        "batterie", "hub", "adaptateur", "webcam", "micro", "enceinte",
        "samsung", "apple", "iphone", "ipad", "macbook", "lenovo", "dell",
        "hp", "asus", "acer", "logitech", "corsair", "razer", "gaming",
        "raspberry", "arduino", "processeur", "ram", "ssd", "cpu", "gpu",
        "bluetooth", "wifi", "routeur", "switch", "ethernet", "hdmi",
    ],
    "Livres & Médias": [
        "livre", "book", "roman", "manga", "bd", "bande dessinée",
        "dvd", "blu-ray", "cd", "vinyl", "jeu vidéo", "journal", "magazine",
        "guide", "manuel", "dictionnaire", "encyclopédie", "audiobook",
    ],
    "Vêtements & Mode": [
        "shirt", "t-shirt", "pantalon", "jean", "robe", "veste", "manteau",
        "chaussure", "sneaker", "basket", "sac", "montre", "bijou", "ceinture",
        "gant", "bonnet", "casquette", "pull", "sweat", "underwear", "slip",
        "boxer", "soutien", "lingerie", "maillot", "collant",
    ],
    "Maison & Cuisine": [
        "cuisine", "casserole", "poêle", "assiette", "verre", "couteau",
        "décoration", "coussin", "lampe", "étagère", "meuble", "aspirateur",
        "robot", "mixeur", "cafetière", "bouilloire", "grille-pain",
        "réfrigérateur", "table", "chaise", "canapé", "lit", "matelas",
        "draps", "couette", "rideau", "poubelle", "ménage", "nettoyage",
    ],
    "Sport & Loisirs": [
        "sport", "fitness", "yoga", "vélo", "running", "football",
        "tennis", "randonnée", "camping", "musculation", "natation",
        "ski", "snowboard", "escalade", "haltère", "kettlebell", "élastique",
        "tapis de course", "gourde", "sac à dos sport",
    ],
    "Santé & Beauté": [
        "shampooing", "crème", "maquillage", "cosmétique", "médicament",
        "vitamines", "masque", "sérum", "dentifrice", "brosse", "rasoir",
        "parfum", "déodorant", "gel douche", "savon", "hydratant",
        "solaire", "santé", "pharmacie", "complément alimentaire",
    ],
    "Alimentation & Épicerie": [
        "food", "nourriture", "café", "thé", "chocolat", "snack",
        "épicerie", "biscuit", "gâteau", "boisson", "eau", "jus",
        "vin", "bière", "spiritueux", "alimentaire", "comestible",
        "infusion", "capsule café", "nespresso",
    ],
    "Jeux & Jouets": [
        "jeu", "jouet", "lego", "figurine", "puzzle", "jeu de société",
        "peluche", "poupée", "voiture jouet", "construction", "kapla",
        "playmobil", "minecraft", "fortnite",
    ],
    "Fournitures & Bureau": [
        "papier", "stylo", "cahier", "classeur", "post-it", "bureau",
        "fourniture", "agenda", "organiseur", "cartouche encre", "toner",
        "chemise", "reliure", "calculatrice", "imprimante", "scotch",
    ],
    "Jardin & Bricolage": [
        "jardin", "plante", "graine", "pot", "arrosoir", "tondeuse",
        "bricolage", "outil", "perceuse", "tournevis", "marteau",
        "vis", "chevilles", "peinture", "enduit", "scie", "pelouse",
    ],
    "Auto & Moto": [
        "voiture", "auto", "moto", "véhicule", "pneu", "huile moteur",
        "filtre", "accessoire voiture", "gps", "dashcam", "siège auto",
        "antivol", "chaine neige",
    ],
    "Bébé & Puériculture": [
        "bébé", "couche", "lait infantile", "nourrisson", "poussette",
        "siège bébé", "jouet bébé", "biberon", "tétine", "parc bébé",
    ],
}

MONTH_NAMES_FR = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]


def categorize_item(item_name: str) -> str:
    item_lower = item_name.lower()
    best_category, best_score = "Autres", 0
    for category, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in item_lower)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category


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
        """Analyze orders scraped directly from Amazon (no PDFs needed)."""
        # Normalise to the same shape _aggregate expects
        invoices = [
            {
                "order_id": o.get("id"),
                "date":     o.get("date"),
                "total":    float(o.get("total", 0) or 0),
                "category": o.get("category", "Autres"),
                "items":    [{"name": n, "price": 0} for n in o.get("items", [])],
            }
            for o in orders
        ]
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
                [{"id": inv.get("order_id", "?"),
                  "date": inv.get("date", ""),
                  "total": inv["total"],
                  "category": inv.get("category", "Autres")}
                 for inv in valid],
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
