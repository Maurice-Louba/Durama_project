from decimal import Decimal
from types import SimpleNamespace

from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (
    Addresse, AvisProduit, Categorie, Commande, CommandeItem, DemandeAppelExpert, EmailOTP,
    Etiquette, Panier, Paiement, Produit, ProduitVariable, SubCategorie, User,
)
from .serializer import (
    AdresseSerialized, AvisProduitSerialized, CommandeSerialized, DemandeAppelExpertSerializer,
    PaiementSerialized, PanierItemSerialized, ProduitSerialized, RegisterSerializer, UserSerialized,
)


def ctx(user):
    return {'request': SimpleNamespace(user=user)}


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="client@test.com", password="MotDePasse!2026")
        cls.autre = User.objects.create_user(email="autre@test.com", password="MotDePasse!2026")
        cls.staff = User.objects.create_user(email="admin@test.com", password="MotDePasse!2026", is_staff=True)
        cls.categorie = Categorie.objects.create(nom="Ciment", courte_description="c", longue_description="l")
        cls.autre_categorie = Categorie.objects.create(nom="Fer", courte_description="c", longue_description="l")
        cls.etiquette = Etiquette.objects.create(name="Promotion", description="d")
        cls.produit = Produit.objects.create(
            nom="Ciment CPA", type_produit="simple", prix_fournisseur=Decimal("100"),
            categorie=cls.categorie, etiquette=cls.etiquette,
        )


class UserSecuriteTests(BaseTestCase):
    def test_pas_de_hash_ni_superuser_expose(self):
        data = UserSerialized(self.user).data
        self.assertNotIn('password', data)
        self.assertNotIn('is_superuser', data)

    def test_utilisateur_ne_peut_pas_se_promouvoir(self):
        s = UserSerialized(self.user, data={'is_staff': True, 'is_superuser': True, 'first_name': 'Ali'}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.first_name, 'Ali')

    def test_inscription_email_normalise_et_doublon_insensible_casse(self):
        s = RegisterSerializer(data={'email': 'CLIENT@test.com', 'password': 'MotDePasse!2026'})
        self.assertFalse(s.is_valid())
        s = RegisterSerializer(data={'email': ' Nouveau@Test.com ', 'password': 'MotDePasse!2026'})
        self.assertTrue(s.is_valid(), s.errors)
        user = s.save()
        self.assertEqual(user.email, 'nouveau@test.com')
        self.assertFalse(user.is_active)

    def test_connexion_insensible_a_la_casse(self):
        self.assertEqual(User.objects.get_by_natural_key('Client@Test.com'), self.user)

    def test_otp_six_chiffres(self):
        otp = EmailOTP.objects.create(user=self.user)
        otp.generate_otp()
        self.assertRegex(otp.otp_code, r'^\d{6}$')


class ProduitTests(BaseTestCase):
    def test_prix_vente_calcule_et_slug_sku_uniques(self):
        self.assertEqual(self.produit.prix_vente, Decimal("120.00"))
        p2 = Produit.objects.create(nom="Ciment CPA", type_produit="simple", prix_fournisseur=1,
                                    categorie=self.categorie, etiquette=self.etiquette)
        self.assertNotEqual(p2.slug, self.produit.slug)
        self.assertNotEqual(p2.sku, self.produit.sku)
        self.assertEqual(p2.etat_stock, 'en stock')

    def test_variante_prix_decimal(self):
        # Plantait avant : Decimal * float -> TypeError
        v = ProduitVariable.objects.create(produit=self.produit, prix_fournisseur=Decimal("50"))
        self.assertEqual(v.prix_vente, Decimal("60.00"))

    def test_increment_views(self):
        self.produit.increment_views()
        self.produit.increment_views()
        self.assertEqual(self.produit.vues, 2)

    def test_prix_fournisseur_cache_au_public(self):
        self.assertNotIn('prix_fournisseur', ProduitSerialized(self.produit).data)
        self.assertNotIn('prix_fournisseur', ProduitSerialized(self.produit, context=ctx(self.user)).data)
        self.assertIn('prix_fournisseur', ProduitSerialized(self.produit, context=ctx(self.staff)).data)

    def test_promo_superieure_refusee(self):
        s = ProduitSerialized(self.produit, data={'prix_promo': '500'}, partial=True)
        self.assertFalse(s.is_valid())
        self.assertIn('prix_promo', s.errors)

    def test_sous_categorie_incoherente_refusee(self):
        sc = SubCategorie.objects.create(categorie_principale=self.autre_categorie, nom="Tiges")
        s = ProduitSerialized(self.produit, data={'sous_categorie_id': sc.id}, partial=True)
        self.assertFalse(s.is_valid())

    def test_compteurs_non_modifiables(self):
        s = ProduitSerialized(self.produit, data={'vues': 9999, 'nombres_ventes': 9999}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.vues, 0)


class PanierTests(BaseTestCase):
    def test_un_seul_panier_actif(self):
        Panier.objects.create(user=self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Panier.objects.create(user=self.user)
        Panier.objects.create(user=self.user, actif=False)  # les anciens paniers inactifs restent possibles
        self.assertEqual(Panier.panier_actif(self.user).user, self.user)

    def test_quantite_invalide_refusee(self):
        for q in (0, -3):
            s = PanierItemSerialized(data={'produit_id': self.produit.id, 'quantite': q}, context=ctx(self.user))
            self.assertFalse(s.is_valid())

    def test_variante_d_un_autre_produit_refusee(self):
        autre = Produit.objects.create(nom="Fer 12", type_produit="variable", prix_fournisseur=1,
                                       categorie=self.categorie, etiquette=self.etiquette)
        v = ProduitVariable.objects.create(produit=autre, prix_fournisseur=1)
        s = PanierItemSerialized(data={'produit_id': self.produit.id, 'produit_variable_id': v.id}, context=ctx(self.user))
        self.assertFalse(s.is_valid())

    def test_rupture_de_stock_refusee(self):
        self.produit.etat_stock = 'rupture stock'
        self.produit.save()
        s = PanierItemSerialized(data={'produit_id': self.produit.id}, context=ctx(self.user))
        self.assertFalse(s.is_valid())

    def test_ajout_ok_et_is_variable_deduit(self):
        v = ProduitVariable.objects.create(produit=self.produit, prix_fournisseur=1)
        s = PanierItemSerialized(data={'produit_id': self.produit.id, 'produit_variable_id': v.id, 'quantite': 2,
                                       'is_variable': False}, context=ctx(self.user))
        self.assertTrue(s.is_valid(), s.errors)
        item = s.save()
        self.assertTrue(item.is_variable)
        self.assertEqual(item.panier.user, self.user)


class CommandeTests(BaseTestCase):
    def test_client_ne_fixe_ni_statut_ni_frais(self):
        s = CommandeSerialized(data={'statut': 'livree', 'frais_livraison': '-50', 'numero': 'X'}, context=ctx(self.user))
        self.assertTrue(s.is_valid(), s.errors)
        c = s.save()
        self.assertEqual(c.statut, 'en_attente')
        self.assertEqual(c.frais_livraison, 0)
        self.assertNotEqual(c.numero, 'X')

    def test_panier_d_un_autre_refuse(self):
        panier_autre = Panier.objects.create(user=self.autre)
        s = CommandeSerialized(data={'panier_id': panier_autre.id}, context=ctx(self.user))
        self.assertFalse(s.is_valid())

    def test_adresse_par_defaut_et_totaux(self):
        Addresse.objects.create(user=self.user, address="Kaloum", ville="Conakry", pays="Guinée",
                                telephone="620000000", latitude=9.5, longitude=-13.7, is_default=True)
        c = Commande.objects.create(user=self.user, frais_livraison=Decimal("10"))
        self.assertIn("Conakry", c.adresse_livraison)
        self.assertEqual(c.latitude, 9.5)
        CommandeItem.objects.create(commande=c, produit=self.produit, quantite=3, prix_unitaire=Decimal("120"))
        c.calculer_totaux()
        self.assertEqual(c.montant_total, Decimal("370.00"))
        self.assertIn(self.user.email, str(c))  # __str__ plantait (self.acheteur)

    def test_paiement_montant_impose_par_serveur(self):
        c = Commande.objects.create(user=self.user)
        CommandeItem.objects.create(commande=c, produit=self.produit, quantite=1, prix_unitaire=Decimal("120"))
        c.calculer_totaux()
        s = PaiementSerialized(data={'methode': 'orange_money', 'montant': '1', 'statut': 'effectue'})
        self.assertTrue(s.is_valid(), s.errors)
        p = s.save(commande=c)
        self.assertEqual(p.montant, Decimal("120.00"))
        self.assertEqual(p.statut, 'en_attente')
        s2 = PaiementSerialized(data={'methode': 'orange_money'})
        self.assertTrue(s2.is_valid())
        with self.assertRaises(Exception):
            s2.save(commande=c)
        self.assertEqual(Paiement.objects.count(), 1)


class AdresseTests(BaseTestCase):
    def test_patch_ne_remet_pas_les_coordonnees_a_zero(self):
        a = Addresse.objects.create(user=self.user, address="A", ville="Conakry", pays="GN",
                                    telephone="620000000", latitude=9.5, longitude=-13.7)
        s = AdresseSerialized(a, data={'ville': 'Kindia'}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        a.refresh_from_db()
        self.assertEqual((a.latitude, a.longitude, a.ville), (9.5, -13.7, 'Kindia'))

    def test_une_seule_adresse_par_defaut(self):
        a1 = Addresse.objects.create(user=self.user, address="A", ville="V", pays="P", telephone="620000000",
                                     latitude=0, longitude=0, is_default=True)
        Addresse.objects.create(user=self.user, address="B", ville="V", pays="P", telephone="620000000",
                                latitude=0, longitude=0, is_default=True)
        a1.refresh_from_db()
        self.assertFalse(a1.is_default)

    def test_coordonnees_hors_limites(self):
        s = AdresseSerialized(data={'address': 'A', 'ville': 'V', 'pays': 'P', 'telephone': '620000000',
                                    'latitude': 200, 'longitude': 0})
        self.assertFalse(s.is_valid())


class AvisTests(BaseTestCase):
    def test_note_hors_limites(self):
        for note in (0, 6):
            s = AvisProduitSerialized(data={'texte': 'ok', 'note': note}, context=ctx(self.user))
            self.assertFalse(s.is_valid())

    def test_pas_d_email_dans_avis_public_et_un_avis_par_produit(self):
        s = AvisProduitSerialized(data={'texte': 'Très bon', 'note': 4}, context=ctx(self.user))
        self.assertTrue(s.is_valid(), s.errors)
        avis = s.save(produit=self.produit)
        self.assertNotIn('email', AvisProduitSerialized(avis).data['user'])
        s2 = AvisProduitSerialized(data={'texte': 'Encore', 'note': 1}, context=ctx(self.user))
        self.assertTrue(s2.is_valid())
        with self.assertRaises(Exception):
            s2.save(produit=self.produit)
        self.assertEqual(AvisProduit.objects.count(), 1)


class DemandeAppelTests(BaseTestCase):
    donnees = {'nom': 'Moussa', 'email': 'M@Test.com', 'telephone': '+224 620 00 00 00',
               'sujet': 'Fondation', 'message': 'Besoin d\'aide'}

    def test_client_ne_peut_pas_changer_statut_ni_usurper(self):
        data = dict(self.donnees, statut='traitee', notes_interne='hack', user_id=self.autre.id)
        s = DemandeAppelExpertSerializer(data=data, context=ctx(self.user))
        self.assertTrue(s.is_valid(), s.errors)
        d = s.save()
        self.assertEqual((d.statut, d.notes_interne, d.user), ('en_attente', None, self.user))
        self.assertEqual(d.email, 'm@test.com')
        self.assertNotIn('notes_interne', DemandeAppelExpertSerializer(d, context=ctx(self.user)).data)

    def test_staff_traite_et_date_traitement_remplie(self):
        d = DemandeAppelExpert.objects.create(user=self.user, **self.donnees)
        s = DemandeAppelExpertSerializer(d, data={'statut': 'traitee'}, partial=True, context=ctx(self.staff))
        self.assertTrue(s.is_valid(), s.errors)
        d = s.save()
        self.assertEqual(d.statut, 'traitee')
        self.assertIsNotNone(d.date_traitement)

    def test_telephone_invalide(self):
        s = DemandeAppelExpertSerializer(data=dict(self.donnees, telephone='abc'), context=ctx(self.user))
        self.assertFalse(s.is_valid())


# =====================================================================
# Tests HTTP des vues
# =====================================================================
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from .models import ContenuPanier, Favori, Livraison, ProjetDevis


class VuesBase(BaseTestCase):
    def setUp(self):
        cache.clear()
        self.client_user = APIClient()
        self.client_user.force_authenticate(self.user)
        self.client_autre = APIClient()
        self.client_autre.force_authenticate(self.autre)
        self.client_staff = APIClient()
        self.client_staff.force_authenticate(self.staff)
        self.anonyme = APIClient()

    def ajouter_au_panier(self, client, produit=None, quantite=1):
        return client.post('/panier/items/', {'produit_id': (produit or self.produit).id, 'quantite': quantite},
                           format='json')


class VuesPermissionsCatalogueTests(VuesBase):
    def test_client_ne_peut_pas_gerer_le_catalogue(self):
        for methode, url in [
            ('post', '/creer-produit/'),
            ('patch', f'/modifier-produit/{self.produit.id}/'),
            ('delete', f'/supprimer-produit/{self.produit.id}/'),
            ('post', '/creer-categorie/'),
            ('delete', f'/supprimer-categorie/{self.categorie.id}/'),
            ('post', '/faire-type-attribut/'),
            ('post', '/creer-etiquette/'),
            ('post', f'/ajouter-image/{self.produit.id}/'),
            ('post', f'/ajouter-variante/{self.produit.id}/'),
        ]:
            r = getattr(self.client_user, methode)(url, {}, format='json')
            self.assertEqual(r.status_code, 403, f"{methode} {url}")
        self.assertEqual(self.anonyme.post('/faire-type-attribut/', {'nom': 'x'}).status_code, 401)

    def test_staff_gere_le_catalogue(self):
        r = self.client_staff.patch(f'/modifier-produit/{self.produit.id}/', {'nom': 'Ciment 42.5'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('prix_fournisseur', r.data)
        r = self.client_staff.post('/faire-type-attribut/', {'nom': 'Couleur'}, format='json')
        self.assertEqual(r.status_code, 201)

    def test_suppression_categorie_avec_produits_bloquee(self):
        r = self.client_staff.delete(f'/supprimer-categorie/{self.categorie.id}/')
        self.assertEqual(r.status_code, 409)
        self.assertTrue(Produit.objects.filter(pk=self.produit.pk).exists())

    def test_produits_non_publies_caches_au_public(self):
        Produit.objects.filter(pk=self.produit.pk).update(est_publie=False)
        self.assertEqual(len(self.anonyme.get('/produits/').data), 0)
        self.assertEqual(self.anonyme.get(f'/produits/{self.produit.slug}/').status_code, 404)
        self.assertEqual(len(self.client_staff.get('/produits/').data), 1)

    def test_prix_fournisseur_jamais_public(self):
        r = self.anonyme.get(f'/produits/{self.produit.slug}/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('prix_fournisseur', r.data)

    def test_attributs_par_variante_plusieurs_variantes(self):
        ProduitVariable.objects.create(produit=self.produit, prix_fournisseur=1)
        ProduitVariable.objects.create(produit=self.produit, prix_fournisseur=2)
        self.assertEqual(self.anonyme.get(f'/variantes/{self.produit.slug}/attributs/').status_code, 200)
        self.assertEqual(self.anonyme.get('/variantes/inconnu/attributs/').status_code, 404)


class VuesUtilisateurTests(VuesBase):
    def test_pas_d_escalade_de_privileges(self):
        r = self.client_user.put('/infoUser/', {'is_staff': True, 'is_superuser': True}, format='json')
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff or self.user.is_superuser)
        self.assertNotIn('password', r.data)


class VuesPanierTests(VuesBase):
    def test_ajout_cumul_et_total(self):
        self.assertEqual(self.ajouter_au_panier(self.client_user, quantite=2).status_code, 201)
        r = self.ajouter_au_panier(self.client_user, quantite=3)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['quantite'], 5)
        self.assertEqual(Decimal(str(self.client_user.get('/prix_total/').data)), Decimal('600'))
        self.assertEqual(self.client_user.get('/nombre_element/').data, 1)

    def test_quantite_invalide(self):
        self.assertEqual(self.ajouter_au_panier(self.client_user, quantite=-4).status_code, 400)
        self.assertEqual(self.ajouter_au_panier(self.client_user, quantite='abc').status_code, 400)

    def test_impossible_de_toucher_le_panier_d_un_autre(self):
        item_id = self.ajouter_au_panier(self.client_user).data['id']
        for methode, url in [('post', f'/changer_quantiter/{item_id}/'), ('post', f'/diminuer_quantiter/{item_id}/'),
                             ('delete', f'/supprimer_un_item/{item_id}/'), ('patch', f'/panier/items/{item_id}/')]:
            r = getattr(self.client_autre, methode)(url, {'quantite': 99}, format='json')
            self.assertEqual(r.status_code, 404, url)
        self.assertEqual(ContenuPanier.objects.get(pk=item_id).quantite, 1)

    def test_promo_appliquee_au_total(self):
        Produit.objects.filter(pk=self.produit.pk).update(prix_promo=Decimal('100'))
        self.ajouter_au_panier(self.client_user, quantite=2)
        self.assertEqual(Decimal(str(self.client_user.get('/prix_total/').data)), Decimal('200'))


class VuesCommandeTests(VuesBase):
    def test_parcours_complet_commande_stock_annulation(self):
        Produit.objects.filter(pk=self.produit.pk).update(quantite=5)
        self.ajouter_au_panier(self.client_user, quantite=3)
        r = self.client_user.post('/commande/faire/', {'notes': 'Livrer le matin'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data['montant_total']), Decimal('360.00'))
        self.assertEqual(len(r.data['items']), 1)
        self.produit.refresh_from_db()
        self.assertEqual((self.produit.quantite, self.produit.nombres_ventes), (2, 3))
        # le panier est fermé : un nouveau panier vide est utilisé ensuite
        self.assertEqual(self.client_user.get('/nombre_element/').data, 0)

        commande_id = r.data['id']
        r = self.client_user.patch(f'/commande/modifier/{commande_id}/', {'statut': 'annulee'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['statut'], 'annulee')
        self.produit.refresh_from_db()
        self.assertEqual((self.produit.quantite, self.produit.nombres_ventes), (5, 0))

    def test_stock_insuffisant_rien_n_est_cree(self):
        Produit.objects.filter(pk=self.produit.pk).update(quantite=2)
        self.ajouter_au_panier(self.client_user, quantite=3)
        r = self.client_user.post('/commande/faire/', {}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Stock insuffisant', r.data['message'])
        self.assertEqual(Commande.objects.count(), 0)
        self.assertEqual(self.client_user.get('/nombre_element/').data, 1)  # le panier est intact

    def test_panier_vide(self):
        r = self.client_user.post('/commande/faire/', {}, format='json')
        self.assertIn(r.status_code, (400, 404))
        self.assertEqual(Commande.objects.count(), 0)

    def test_confidentialite_des_commandes(self):
        self.ajouter_au_panier(self.client_user)
        self.client_user.post('/commande/faire/', {}, format='json')
        self.assertEqual(len(self.client_autre.get('/commandes/').data), 0)
        self.assertEqual(len(self.client_staff.get('/commandes/').data), 1)
        self.assertEqual(self.client_autre.get(f'/commandes/user/{self.user.id}/').status_code, 403)

    def test_client_ne_peut_pas_passer_sa_commande_en_livree(self):
        self.ajouter_au_panier(self.client_user)
        cid = self.client_user.post('/commande/faire/', {}, format='json').data['id']
        r = self.client_user.patch(f'/commande/modifier/{cid}/', {'statut': 'livree'}, format='json')
        self.assertEqual(r.status_code, 403)
        r = self.client_staff.patch(f'/commande/modifier/{cid}/', {'statut': 'livree'}, format='json')
        self.assertEqual(r.status_code, 400)  # transition en_attente -> livree interdite
        r = self.client_staff.patch(f'/commande/modifier/{cid}/', {'statut': 'acceptee'}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_paiement_et_livraison(self):
        self.ajouter_au_panier(self.client_user)
        cid = self.client_user.post('/commande/faire/', {}, format='json').data['id']
        r = self.client_user.post(f'/paiement/creer/{cid}/', {'methode': 'orange_money', 'montant': '1'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data['montant']), Decimal('120.00'))
        pid = r.data['id']
        self.assertEqual(self.client_autre.get(f'/paiement/{pid}/').status_code, 403)
        self.assertEqual(self.client_user.patch(f'/paiement/{pid}/update/', {'statut': 'effectue'}, format='json').status_code, 403)
        r = self.client_staff.patch(f'/paiement/{pid}/update/', {'statut': 'effectue'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.data['date_paiement'])

        self.assertEqual(self.client_user.post(f'/livraison/creer/{cid}/', {}, format='json').status_code, 403)
        r = self.client_staff.post('/creer-une-livraison/', {'commande_id': cid, 'transporteur': 'DHL'}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client_user.get(f'/livraisons/commande/{cid}/').status_code, 200)
        self.assertEqual(self.client_autre.get(f'/livraisons/commande/{cid}/').status_code, 403)
        self.assertEqual(Livraison.objects.count(), 1)


class VuesAvisFavorisTests(VuesBase):
    def test_avis_anonyme_refuse_et_suppression_de_son_avis(self):
        self.assertEqual(self.anonyme.post(f'/faire-avis-sur-un-produit/{self.produit.id}/', {'texte': 'x'}).status_code, 401)
        r = self.client_user.post(f'/faire-avis-sur-un-produit/{self.produit.id}/', {'texte': 'Top', 'note': 5}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.anonyme.get(f'/details-avis-produit/{r.data["id"]}/').status_code, 200)
        self.assertEqual(self.client_user.patch(f'/modifier-avis-produit/{self.produit.id}/', {'note': 3}, format='json').status_code, 200)
        self.assertEqual(self.client_autre.delete(f'/supprimer-avis-produit/{self.produit.id}/').status_code, 404)
        self.assertEqual(self.client_user.delete(f'/supprimer-avis-produit/{self.produit.id}/').status_code, 204)
        self.assertTrue(Produit.objects.filter(pk=self.produit.pk).exists())  # le produit n'est PAS supprimé

    def test_favoris(self):
        self.assertEqual(self.anonyme.get('/listProduitFavori/').status_code, 401)
        self.assertEqual(self.client_user.post(f'/unProduitCommeFavorie/{self.produit.id}/').status_code, 201)
        self.assertEqual(self.client_user.delete(f'/supprimer_favori/{self.produit.id}/').status_code, 204)
        self.assertEqual(self.client_user.delete(f'/supprimer_favori/{self.produit.id}/').status_code, 404)
        self.assertEqual(Favori.objects.count(), 0)


class VuesDevisAppelTests(VuesBase):
    def test_devis_generation_detail_et_validation(self):
        r = self.client_user.post('/devis/', {'ville': 'Conakry', 'surface': 100, 'options': ['plomberie']}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        devis_id = r.data['id']
        self.assertGreater(Decimal(r.data['prix_estime']), 0)
        self.assertEqual(self.client_user.get(f'/deviss/{devis_id}/').status_code, 200)
        self.assertEqual(self.client_autre.get(f'/deviss/{devis_id}/').status_code, 404)
        self.assertEqual(self.client_user.post('/devis/', {'ville': 'Conakry', 'surface': 'abc'}, format='json').status_code, 400)
        self.assertEqual(self.client_user.post('/devis/', {'ville': 'Conakry', 'surface': 50, 'nombre_etages': -2}, format='json').status_code, 400)
        self.assertEqual(self.anonyme.post('/devis/', {'ville': 'Conakry', 'surface': 100}, format='json').status_code, 401)
        self.assertEqual(self.client_user.delete(f'/devis/{devis_id}/').status_code, 200)
        self.assertEqual(ProjetDevis.objects.count(), 0)

    def test_demandes_appel_confidentielles(self):
        donnees = {'nom': 'Moussa', 'email': 'm@test.com', 'telephone': '620000000', 'sujet': 'S', 'message': 'M'}
        self.assertEqual(self.client_user.post('/demandes-appel/creer/', donnees, format='json').status_code, 201)
        self.assertEqual(self.client_autre.get('/demandes-appel/').data['count'], 0)
        self.assertEqual(self.client_staff.get('/demandes-appel/').data['count'], 1)
        self.assertEqual(self.client_autre.get('/demandes-appel/statistiques/').status_code, 403)
        self.assertEqual(self.client_staff.get('/demandes-appel/statistiques/').data['en_attente'], 1)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class VuesInscriptionOTPTests(VuesBase):
    def test_inscription_verification_et_force_brute(self):
        r = self.anonyme.post('/register/', {'email': 'neuf@test.com', 'password': 'MotDePasse!2026'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        code = EmailOTP.objects.get(user__email='neuf@test.com').otp_code
        mauvais = '000000' if code != '000000' else '111111'
        for _ in range(5):
            self.anonyme.post('/verify_otp/', {'email': 'neuf@test.com', 'otp': mauvais}, format='json')
        # après 5 essais faux, le code est invalidé : même le bon code ne marche plus
        r = self.anonyme.post('/verify_otp/', {'email': 'neuf@test.com', 'otp': code}, format='json')
        self.assertEqual(r.status_code, 400)

        self.assertEqual(self.anonyme.post('/resend_otp/', {'email': 'neuf@test.com'}, format='json').status_code, 200)
        code = EmailOTP.objects.get(user__email='neuf@test.com').otp_code
        r = self.anonyme.post('/verify_otp/', {'email': 'NEUF@test.com', 'otp': code}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn('access', r.data)
        self.assertTrue(User.objects.get(email='neuf@test.com').is_active)

    def test_limite_de_debit_otp(self):
        codes = [self.anonyme.post('/verify_otp/', {'email': 'x@test.com', 'otp': '123456'}, format='json').status_code
                 for _ in range(12)]
        self.assertIn(429, codes)


# =====================================================================
# Configuration : connexion, admin, médias
# =====================================================================
from django.test import Client
from rest_framework.authtoken.models import Token


class ConfigurationTests(VuesBase):
    def test_connexion_jwt_et_limite_de_debit(self):
        r = self.anonyme.post('/api/token/', {'email': 'client@test.com', 'password': 'MotDePasse!2026'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        codes = [self.anonyme.post('/jwt/create/', {'email': 'client@test.com', 'password': 'faux'}, format='json').status_code
                 for _ in range(12)]
        self.assertIn(429, codes)

    def test_jeton_drf_refuse(self):
        token = Token.objects.create(user=self.staff)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        self.assertEqual(c.get('/infoUser/').status_code, 401)

    def test_pages_admin(self):
        c = Client()
        c.force_login(self.staff)
        self.staff.is_superuser = True
        self.staff.save()
        for url in ['/admin/', '/admin/DuramaProject/commande/?q=test', '/admin/DuramaProject/user/add/',
                    '/admin/DuramaProject/produit/', '/admin/DuramaProject/demandeappelexpert/',
                    '/admin/DuramaProject/projetdevis/', f'/admin/DuramaProject/produit/{self.produit.id}/change/']:
            self.assertEqual(c.get(url).status_code, 200, url)

    def test_creation_utilisateur_via_admin(self):
        c = Client()
        self.staff.is_superuser = True
        self.staff.save()
        c.force_login(self.staff)
        r = c.post('/admin/DuramaProject/user/add/', {
            'email': 'Admin.Cree@Test.com', 'password1': 'MotDePasse!2026', 'password2': 'MotDePasse!2026',
            'usable_password': 'true', 'is_active': 'on',
        })
        self.assertEqual(r.status_code, 302, r.content[:500])
        self.assertTrue(User.objects.filter(email='admin.cree@test.com').exists())

    def test_annulation_depuis_admin_remet_le_stock(self):
        Produit.objects.filter(pk=self.produit.pk).update(quantite=5)
        self.ajouter_au_panier(self.client_user, quantite=2)
        cid = self.client_user.post('/commande/faire/', {}, format='json').data['id']
        self.staff.is_superuser = True
        self.staff.save()
        c = Client()
        c.force_login(self.staff)
        r = c.post('/admin/DuramaProject/commande/', {'action': 'action_annuler_commandes', '_selected_action': [cid]})
        self.assertEqual(r.status_code, 302)
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.quantite, 5)
        self.assertEqual(Commande.objects.get(pk=cid).statut, 'annulee')


class CompatibiliteFrontendTests(VuesBase):
    def test_urls_images_relatives_meme_avec_contexte(self):
        # Le frontend préfixe lui-même l'URL de l'API : le backend doit renvoyer « /media/... »
        Produit.objects.filter(pk=self.produit.pk).update(image_principale='produits/principales/ciment.JPG')
        r = self.anonyme.get(f'/produits/{self.produit.slug}/')
        self.assertEqual(r.data['image_principale'], '/media/produits/principales/ciment.JPG')
        self.ajouter_au_panier(self.client_user)
        item = self.client_user.get('/panier/items/').data[0]
        self.assertEqual(item['produit']['image_principale'], '/media/produits/principales/ciment.JPG')

    def test_profil_formdata_telephone_vide(self):
        r = self.client_user.put('/infoUser/', {'first_name': 'Awa', 'phone_number': 'null'}, format='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['phone_number'], '')
        self.assertIsNone(r.data['photo'])

    def test_rafraichissement_renvoie_un_nouveau_refresh(self):
        r = self.anonyme.post('/api/token/', {'email': 'client@test.com', 'password': 'MotDePasse!2026'}, format='json')
        ancien = r.data['refresh']
        r = self.anonyme.post('/api/token/refresh/', {'refresh': ancien}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('refresh', r.data)
        # l'ancien est invalidé : le frontend DOIT garder le nouveau
        self.assertEqual(self.anonyme.post('/api/token/refresh/', {'refresh': ancien}, format='json').status_code, 401)
        self.assertEqual(self.anonyme.post('/api/token/refresh/', {'refresh': r.data['refresh']}, format='json').status_code, 200)



# =====================================================================
# Mot de passe oublié et page Contact
# =====================================================================
from .models import MessageContact


class VuesMotDePasseOublieTests(VuesBase):
    def test_email_inconnu_meme_reponse_sans_envoi(self):
        r = self.anonyme.post('/mot-de-passe-oublie/', {'email': 'inconnu@test.com'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_reinitialisation_complete(self):
        # Une session ouverte avant la réinitialisation
        connexion = self.anonyme.post('/api/token/', {'email': 'client@test.com', 'password': 'MotDePasse!2026'}, format='json')
        ancien_refresh = connexion.data['refresh']

        r = self.anonyme.post('/mot-de-passe-oublie/', {'email': 'CLIENT@test.com'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        code = EmailOTP.objects.get(user=self.user).otp_code
        self.assertIn(code, mail.outbox[0].body)

        mauvais = '000000' if code != '000000' else '111111'
        r = self.anonyme.post('/reinitialiser-mot-de-passe/', {'email': 'client@test.com', 'code': mauvais, 'mot_de_passe': 'NouveauMdp!2026'}, format='json')
        self.assertEqual(r.status_code, 400)
        r = self.anonyme.post('/reinitialiser-mot-de-passe/', {'email': 'client@test.com', 'code': code, 'mot_de_passe': '12345678'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('mot_de_passe', r.data)

        r = self.anonyme.post('/reinitialiser-mot-de-passe/', {'email': 'client@test.com', 'code': code, 'mot_de_passe': 'NouveauMdp!2026'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NouveauMdp!2026'))
        # Le code ne sert qu'une fois, et l'ancienne session est révoquée
        r = self.anonyme.post('/reinitialiser-mot-de-passe/', {'email': 'client@test.com', 'code': code, 'mot_de_passe': 'AutreMdp!2026'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.anonyme.post('/api/token/refresh/', {'refresh': ancien_refresh}, format='json').status_code, 401)

    def test_force_brute_invalide_le_code(self):
        self.anonyme.post('/mot-de-passe-oublie/', {'email': 'client@test.com'}, format='json')
        code = EmailOTP.objects.get(user=self.user).otp_code
        mauvais = '000000' if code != '000000' else '111111'
        for _ in range(5):
            self.anonyme.post('/reinitialiser-mot-de-passe/', {'email': 'client@test.com', 'code': mauvais, 'mot_de_passe': 'NouveauMdp!2026'}, format='json')
        r = self.anonyme.post('/reinitialiser-mot-de-passe/', {'email': 'client@test.com', 'code': code, 'mot_de_passe': 'NouveauMdp!2026'}, format='json')
        self.assertEqual(r.status_code, 400)


class VuesContactTests(VuesBase):
    donnees = {'nom': 'Awa Camara', 'email': 'Awa@Exemple.com', 'telephone': '+224 622 00 00 00',
               'sujet': 'Livraison à Kipé', 'message': 'Bonjour, livrez-vous à Kipé le samedi ?'}

    def test_message_anonyme_enregistre(self):
        r = self.anonyme.post('/contact/', self.donnees, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        m = MessageContact.objects.get()
        self.assertEqual(m.email, 'awa@exemple.com')
        self.assertIsNone(m.user)
        self.assertFalse(m.traite)

    def test_message_utilisateur_connecte_lie_au_compte(self):
        self.assertEqual(self.client_user.post('/contact/', self.donnees, format='json').status_code, 201)
        self.assertEqual(MessageContact.objects.get().user, self.user)

    def test_validation(self):
        r = self.anonyme.post('/contact/', {**self.donnees, 'message': 'court', 'email': 'pas-un-email'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('message', r.data)
        self.assertIn('email', r.data)
        self.assertEqual(MessageContact.objects.count(), 0)

    @override_settings(EMAIL_HOST_USER='equipe@durama.test')
    def test_equipe_prevenue_par_email(self):
        self.anonyme.post('/contact/', self.donnees, format='json')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['equipe@durama.test'])

    def test_anti_spam(self):
        codes = [self.anonyme.post('/contact/', self.donnees, format='json').status_code for _ in range(7)]
        self.assertIn(429, codes)



class ChargerDemoTests(BaseTestCase):
    def test_chargement_idempotent_puis_suppression(self):
        from django.core.management import call_command
        from io import StringIO
        call_command("charger_demo", stdout=StringIO())
        nb = Produit.objects.filter(sku__startswith="DEMO-").count()
        self.assertGreater(nb, 20)
        self.assertTrue(Produit.objects.filter(sku__startswith="DEMO-", categorie__gros_categorie="securité").exists())
        call_command("charger_demo", stdout=StringIO())  # pas de doublons
        self.assertEqual(Produit.objects.filter(sku__startswith="DEMO-").count(), nb)
        call_command("charger_demo", "--supprimer", stdout=StringIO())
        self.assertFalse(Produit.objects.filter(sku__startswith="DEMO-").exists())
        self.assertTrue(Produit.objects.filter(pk=self.produit.pk).exists())  # les vrais produits restent
