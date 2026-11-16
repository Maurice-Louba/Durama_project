"""
Données de démonstration (phase de développement) : vendeurs, catégories, produits, avis.

    python manage.py charger_demo              # crée ou met à jour (sans doublons)
    python manage.py charger_demo --supprimer  # retire toutes les données de démo

Les produits de démo ont un SKU qui commence par « DEMO- » ; leurs photos sont dans media/demo/.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from DuramaProject.models import AvisProduit, Categorie, Etiquette, Produit, User, Vendeur

PREFIXE = "DEMO-"
DOMAINE_COMPTES = "@demo.durama.local"

VENDEURS = [
    {"slug": "demo-quincaillerie-kaloum", "nom_boutique": "Quincaillerie Kaloum", "telephone": "+224620000001",
     "description": "Matériaux de gros œuvre et quincaillerie depuis 2012.", "adresse": "Kaloum, Conakry"},
    {"slug": "demo-btp-materiaux-guinee", "nom_boutique": "BTP Matériaux Guinée", "telephone": "+224620000002",
     "description": "Carrelage, sanitaires, peinture et finitions.", "adresse": "Matoto, Conakry"},
    {"slug": "demo-securipro-conakry", "nom_boutique": "SécuriPro Conakry", "telephone": "+224620000003",
     "description": "Équipements de protection individuelle pour chantiers.", "adresse": "Kipé, Ratoma"},
]

ETIQUETTES = {
    "nouveaute": ("Nouveauté", "Produit récemment ajouté au catalogue"),
    "meilleure-vente": ("Meilleure vente", "Parmi les produits les plus commandés"),
}

# nom -> (rayon, courte description)
CATEGORIES = {
    "Ciment et béton": ("gros-oeuvres", "Ciments, bétons et mortiers pour fondations et structures."),
    "Fer à béton": ("gros-oeuvres", "Barres, treillis et fil d'attache pour le béton armé."),
    "Sable et gravier": ("gros-oeuvres", "Granulats livrés en vrac sur chantier."),
    "Carrelage": ("second-oeuvres", "Carreaux de sol et faïence murale."),
    "Peinture": ("second-oeuvres", "Peintures intérieures, extérieures et accessoires."),
    "Plomberie et sanitaires": ("second-oeuvres", "Tuyaux, raccords, robinetterie et sanitaires."),
    "Électricité": ("second-oeuvres", "Câbles, prises, interrupteurs et protections."),
    "Outillage à main": ("outillage", "Marteaux, clés et outils du quotidien sur chantier."),
    "Casques et protections": ("securité", "Casques de chantier, lunettes et protections auditives."),
    "Gants de travail": ("securité", "Gants de manutention, de maçonnerie et anti-coupure."),
    "Vêtements de chantier": ("securité", "Gilets haute visibilité et tenues de travail."),
}

# (sku, nom, catégorie, vendeur, image, prix fournisseur, prix vente, prix promo, stock, état, ventes, étiquette, livraison gratuite, description)
PRODUITS = [
    ("CIM-50", "Ciment CPJ 42.5 — sac de 50 kg", "Ciment et béton", 0, "ciment.jpg", 78000, 92000, 85000, 400, "en stock", 320, "meilleure-vente", False,
     "Ciment Portland composé, idéal pour bétons armés, dalles et fondations. Sac de 50 kg."),
    ("CIM-COL", "Colle à carrelage — sac de 25 kg", "Ciment et béton", 1, "ciment.jpg", 52000, 65000, 0, 120, "en stock", 85, None, False,
     "Mortier-colle pour la pose de carrelage en intérieur et extérieur."),
    ("FER-10", "Fer à béton HA 10 mm — barre de 12 m", "Fer à béton", 0, "fer.jpg", 70000, 82000, 0, 600, "en stock", 210, "meilleure-vente", False,
     "Barre haute adhérence Ø10 mm pour poutres, chaînages et dalles."),
    ("FER-12", "Fer à béton HA 12 mm — barre de 12 m", "Fer à béton", 0, "fer.jpg", 98000, 115000, 108000, 450, "en stock", 175, None, False,
     "Barre haute adhérence Ø12 mm pour poteaux et fondations."),
    ("FER-TRE", "Treillis soudé 2,4 × 6 m", "Fer à béton", 0, "treillis.jpg", 215000, 245000, 0, 60, "en stock", 40, "nouveaute", False,
     "Panneau de treillis soudé pour dallages et chapes."),
    ("FER-FIL", "Fil d'attache recuit — rouleau de 25 kg", "Fer à béton", 0, "fer-ligature.jpg", 160000, 185000, 0, 35, "en stock", 22, None, False,
     "Fil recuit pour ligaturer les armatures."),
    ("SAB-6M3", "Sable de rivière — benne de 6 m³", "Sable et gravier", 0, "gravier.jpg", 900000, 1050000, 0, 0, "sur commande", 30, None, True,
     "Sable lavé pour béton et maçonnerie, livré en benne sur votre chantier."),
    ("GRA-6M3", "Gravier concassé 15/25 — benne de 6 m³", "Sable et gravier", 0, "gravier.jpg", 1200000, 1400000, 1320000, 0, "sur commande", 26, None, True,
     "Gravier concassé calibré 15/25 pour bétons de structure."),
    ("BRI-15", "Parpaing creux 15 × 20 × 40 cm", "Briques", 0, "briques.jpg", 5500, 7000, 0, 3000, "en stock", 540, "meilleure-vente", False,
     "Bloc de béton creux pour murs porteurs et cloisons. Prix à l'unité."),
    ("CAR-6060", "Carrelage grès cérame 60 × 60 cm — le m²", "Carrelage", 1, "carrelage.jpg", 120000, 145000, 130000, 300, "en stock", 95, "nouveaute", False,
     "Grès cérame émaillé aspect pierre, pour sols intérieurs. Prix au m²."),
    ("CAR-FAI", "Faïence murale 25 × 40 cm — le m²", "Carrelage", 1, "carrelage.jpg", 85000, 99000, 0, 180, "en stock", 48, None, False,
     "Faïence brillante pour cuisines et salles de bain. Prix au m²."),
    ("PEI-20L", "Peinture acrylique blanc mat — 20 L", "Peinture", 1, "peinture.jpg", 320000, 380000, 340000, 50, "en stock", 64, "meilleure-vente", False,
     "Peinture intérieure lessivable, haut pouvoir couvrant (environ 120 m² par seau)."),
    ("PEI-ROU", "Kit rouleau et bac de peinture", "Peinture", 1, "rouleau.jpg", 55000, 69000, 0, 75, "en stock", 37, None, False,
     "Rouleau 230 mm, manche télescopique et bac. Pour murs et plafonds."),
    ("PLO-PVC", "Tube PVC évacuation Ø100 — 4 m", "Plomberie et sanitaires", 1, "plomberie.jpg", 58000, 70000, 0, 140, "en stock", 52, None, False,
     "Tube PVC rigide pour évacuation des eaux usées."),
    ("PLO-WC", "Pack WC céramique avec réservoir", "Plomberie et sanitaires", 1, "sanitaires.jpg", 950000, 1150000, 1050000, 12, "en stock", 9, "nouveaute", True,
     "WC à poser avec réservoir double chasse et abattant."),
    ("ELE-CAB", "Câble électrique 2,5 mm² — rouleau de 100 m", "Électricité", 1, "electricite.jpg", 360000, 420000, 0, 40, "en stock", 44, None, False,
     "Câble rigide pour circuits de prises. Rouleau de 100 m."),
    ("ELE-PRI", "Prise de courant encastrable — lot de 10", "Électricité", 1, "electricite.jpg", 95000, 115000, 99000, 4, "en stock", 18, None, False,
     "Prises 2P+T 16 A à encastrer, blanches."),
    ("OUT-MAR", "Marteau de coffreur 600 g", "Outillage à main", 0, "marteau.jpg", 62000, 75000, 0, 60, "en stock", 70, None, False,
     "Marteau à manche fibre anti-vibrations, tête forgée."),
    ("OUT-KIT", "Kit marteau et clé à molette", "Outillage à main", 0, "cle-marteau.jpg", 125000, 150000, 135000, 25, "en stock", 21, "nouveaute", False,
     "Marteau de charpentier et clé à molette 250 mm."),
    ("OUT-ETA", "Établi de chantier avec rangements", "Outillage à main", 0, "atelier.jpg", 780000, 920000, 0, 0, "rupture stock", 6, None, False,
     "Établi pliable robuste avec rangement pour outils."),
    ("SEC-CAS", "Casque de chantier jaune réglable", "Casques et protections", 2, "casque.jpg", 38000, 50000, 45000, 200, "en stock", 260, "meilleure-vente", False,
     "Casque ABS ventilé avec serre-tête à crémaillère. Norme EN 397."),
    ("SEC-KIT", "Kit sécurité : casque et gants", "Casques et protections", 2, "gants-casque.jpg", 70000, 89000, 0, 80, "en stock", 58, "nouveaute", False,
     "Un casque de chantier et une paire de gants de manutention."),
    ("SEC-GAN", "Gants de manutention renforcés — la paire", "Gants de travail", 2, "gants.jpg", 18000, 25000, 0, 500, "en stock", 410, "meilleure-vente", False,
     "Gants enduits latex, bonne prise sur les matériaux humides."),
    ("SEC-GAC", "Gants anti-coupure niveau 5 — la paire", "Gants de travail", 2, "gants.jpg", 42000, 55000, 49000, 3, "en stock", 33, None, False,
     "Protection maximale pour la manipulation de tôles et de verre."),
    ("SEC-GIL", "Gilet haute visibilité jaune", "Vêtements de chantier", 2, "gilet.jpg", 22000, 30000, 0, 300, "en stock", 190, None, True,
     "Gilet fluorescent à bandes réfléchissantes. Taille unique réglable."),
    ("SEC-TEN", "Tenue de chantier complète (gilet + casque)", "Vêtements de chantier", 2, "gilet-chantier.jpg", 75000, 95000, 85000, 40, "en stock", 27, "nouveaute", True,
     "Ensemble gilet haute visibilité et casque pour l'accueil de chantier."),
]

COMPTES_AVIS = [("Mamadou", "Diallo"), ("Aïssatou", "Bah"), ("Ibrahima", "Camara")]
AVIS = [
    ("CIM-50", [(5, "Ciment de bonne qualité, livré rapidement sur le chantier à Kipé."), (4, "Bon rapport qualité-prix.")]),
    ("SEC-CAS", [(5, "Léger et confortable, mes ouvriers l'adoptent."), (5, "Bonne qualité pour le prix.")]),
    ("SEC-GAN", [(4, "Solides, tiennent bien sur plusieurs semaines.")]),
    ("BRI-15", [(5, "Parpaings bien calibrés, très peu de casse.")]),
    ("PEI-20L", [(4, "Couvre bien en deux couches.")]),
]


class Command(BaseCommand):
    help = "Charge (ou supprime avec --supprimer) les données de démonstration de Durama."

    def add_arguments(self, parser):
        parser.add_argument("--supprimer", action="store_true", help="Supprime les données de démonstration")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["supprimer"]:
            n_prod, _ = Produit.objects.filter(sku__startswith=PREFIXE).delete()
            Vendeur.objects.filter(slug__startswith="demo-").delete()
            User.objects.filter(email__endswith=DOMAINE_COMPTES).delete()
            Categorie.objects.filter(nom__in=CATEGORIES, produits__isnull=True).delete()
            self.stdout.write(self.style.SUCCESS(f"Données de démo supprimées ({n_prod} objets produits/liés)."))
            return

        vendeurs = []
        for v in VENDEURS:
            obj, _ = Vendeur.objects.update_or_create(slug=v["slug"], defaults=v)
            vendeurs.append(obj)

        etiquettes = {}
        for cle, (nom, desc) in ETIQUETTES.items():
            etiquettes[cle], _ = Etiquette.objects.get_or_create(name=nom, defaults={"description": desc})
        defaut = Etiquette.objects.order_by("id").first() or etiquettes["nouveaute"]

        categories = {}
        for nom, (rayon, desc) in CATEGORIES.items():
            categories[nom], _ = Categorie.objects.update_or_create(
                nom=nom, defaults={"gros_categorie": rayon, "courte_description": desc, "longue_description": desc}
            )
        # « Briques » existe déjà dans la base de développement
        categories["Briques"], _ = Categorie.objects.get_or_create(
            nom="Briques", defaults={"gros_categorie": "gros-oeuvres", "courte_description": "Briques et parpaings", "longue_description": "Briques et parpaings"}
        )

        maintenant = timezone.now()
        crees = 0
        for i, (code, nom, cat, iv, image, fourn, vente, promo, stock, etat, ventes, etiq, livraison, desc) in enumerate(PRODUITS):
            _, cree = Produit.objects.update_or_create(
                sku=PREFIXE + code,
                defaults={
                    "nom": nom,
                    "type_produit": "simple",
                    "vendeur": vendeurs[iv],
                    "categorie": categories[cat],
                    "etiquette": etiquettes.get(etiq) if etiq else defaut,
                    "image_principale": f"demo/{image}",
                    "prix_fournisseur": Decimal(fourn),
                    "prix_vente": Decimal(vente),
                    "prix_promo": Decimal(promo),
                    "quantite": stock,
                    "etat_stock": etat,
                    "nombres_ventes": ventes,
                    "livraison_gratuite": livraison,
                    "description_courte": desc,
                    "description_longue": f"{desc}\n\nProduit de démonstration Durama (phase de développement).",
                    "est_publie": True,
                    "status": "en_vedette" if etiq == "meilleure-vente" else "publie",
                },
            )
            crees += cree
            # Dates étalées pour que le tri « Nouveautés » ait un sens
            Produit.objects.filter(sku=PREFIXE + code).update(created_at=maintenant - timedelta(days=i * 2))

        comptes = []
        for prenom, nom in COMPTES_AVIS:
            u, cree = User.objects.get_or_create(
                email=f"{prenom.lower().replace('ï', 'i')}.{nom.lower()}{DOMAINE_COMPTES}",
                defaults={"first_name": prenom, "last_name": nom, "is_active": True, "is_confirmed": True},
            )
            if cree:
                u.set_unusable_password()
                u.save(update_fields=["password"])
            comptes.append(u)
        for code, avis in AVIS:
            produit = Produit.objects.get(sku=PREFIXE + code)
            for (note, texte), compte in zip(avis, comptes):
                AvisProduit.objects.update_or_create(user=compte, produit=produit, defaults={"note": note, "texte": texte})

        self.stdout.write(self.style.SUCCESS(
            f"Démo prête : {len(PRODUITS)} produits ({crees} nouveaux), {len(vendeurs)} vendeurs, "
            f"{len(CATEGORIES)} catégories, {sum(len(a) for _, a in AVIS)} avis."
        ))
